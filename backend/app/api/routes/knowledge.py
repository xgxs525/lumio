from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.ai import AIConversation, AIMessage
from app.models.document import Document
from app.models.drive import WorkspaceFile
from app.models.knowledge import KbChunk, KbChunkEmbedding, KbKnowledgeBase, KbSource
from app.models.operations import AuditLog, UsageRecord
from app.models.user import User
from app.services.billing import assert_ai_quota
from app.services.bootstrap import ensure_user_workspace
from app.services.file_ai import answer_question, build_chunks, embed_text, embedding_model_name, parse_file_bytes, rank_chunks
from app.services.storage import get_storage

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge"])


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = ""
    visibility: str = Field(default="private", pattern="^(private|workspace|public)$")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|workspace|public)$")


class KnowledgeSourceCreate(BaseModel):
    source_type: str = Field(default="document", max_length=40)
    source_id: str | None = None
    title: str | None = Field(default=None, max_length=500)


class KnowledgeAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=12)


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


async def _knowledge_payload(db: AsyncSession, item: KbKnowledgeBase) -> dict:
    source_count = await db.scalar(
        select(func.count(KbSource.id)).where(KbSource.knowledge_base_id == item.id)
    )
    chunk_count = await db.scalar(select(func.count(KbChunk.id)).where(KbChunk.knowledge_base_id == item.id))
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "name": item.name,
        "description": item.description,
        "visibility": item.visibility,
        "createdBy": str(item.user_id) if item.user_id else None,
        "sourceCount": source_count or 0,
        "chunkCount": chunk_count or 0,
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


def _source_payload(item: KbSource) -> dict:
    source_identifier = str(item.file_id or item.document_id or item.url or "")
    return {
        "id": str(item.id),
        "knowledgeBaseId": str(item.knowledge_base_id),
        "sourceType": item.source_type,
        "sourceId": source_identifier,
        "syncStatus": item.status,
        "metadata": item.metadata_ or {},
        "chunkCount": item.chunk_count or 0,
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


async def _get_knowledge_in_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    knowledge_base_id: str,
) -> KbKnowledgeBase:
    kb_uuid = _uuid_or_400(knowledge_base_id)
    result = await db.execute(
        select(KbKnowledgeBase).where(
            KbKnowledgeBase.id == kb_uuid,
            KbKnowledgeBase.workspace_id == workspace_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return item


async def _clear_source_chunks(
    db: AsyncSession,
    *,
    knowledge_base_id: uuid.UUID,
    source_record_id: uuid.UUID,
) -> None:
    # Find chunk_ids for this source, then delete embeddings + chunks
    chunk_result = await db.execute(
        select(KbChunk.id).where(
            KbChunk.knowledge_base_id == knowledge_base_id,
            KbChunk.source_id == source_record_id,
        )
    )
    chunk_ids = [row[0] for row in chunk_result.all()]
    if chunk_ids:
        await db.execute(
            delete(KbChunkEmbedding).where(KbChunkEmbedding.chunk_id.in_(chunk_ids))
        )
        await db.execute(delete(KbChunk).where(KbChunk.id.in_(chunk_ids)))


async def _index_source(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    knowledge_base_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    source_record_id: uuid.UUID,
) -> dict:
    file_id: uuid.UUID | None = None
    title = "资料来源"
    text = ""
    parser = "manual"

    if source_type == "file":
        result = await db.execute(
            select(WorkspaceFile).where(
                WorkspaceFile.id == source_id,
                WorkspaceFile.workspace_id == workspace_id,
                WorkspaceFile.deleted_at.is_(None),
            )
        )
        file_item = result.scalar_one_or_none()
        if file_item is None:
            raise HTTPException(status_code=404, detail="文件不存在")
        data = await get_storage().read(file_item.storage_key)
        parsed = parse_file_bytes(file_item.name, file_item.extension, data)
        title = file_item.name
        text = parsed.text
        parser = parsed.parser
        file_id = file_item.id
        file_item.parse_status = "parsed"
        file_item.ai_status = "ready"
    elif source_type == "document":
        result = await db.execute(
            select(Document).where(
                Document.id == source_id,
                Document.workspace_id == workspace_id,
                Document.deleted_at.is_(None),
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        title = document.title
        text = document.content_text or document.title
        parser = "document"
    else:
        text = f"手动资料来源：{source_id}"

    await _clear_source_chunks(
        db,
        knowledge_base_id=knowledge_base_id,
        source_record_id=source_record_id,
    )
    chunks = build_chunks(text, source_title=title)
    for chunk_data in chunks:
        chunk_id = uuid.uuid4()
        content = str(chunk_data["content"])
        chunk = KbChunk(
            id=chunk_id,
            knowledge_base_id=knowledge_base_id,
            source_id=source_record_id,
            title=title,
            chunk_index=int(chunk_data["chunk_index"]),
            content=content,
            content_hash=None,
            token_count=0,
            char_count=len(content),
            metadata_=chunk_data.get("metadata", {}),
        )
        embedding = KbChunkEmbedding(
            chunk_id=chunk_id,
            embedding_model_name=embedding_model_name(),
            embedding=embed_text(content),
        )
        db.add(chunk)
        db.add(embedding)
    return {"title": title, "parser": parser, "chunkCount": len(chunks), "characters": len(text)}


async def _load_kb_chunks(db: AsyncSession, *, knowledge_base_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(KbChunk, KbChunkEmbedding.embedding)
        .join(KbChunkEmbedding, KbChunkEmbedding.chunk_id == KbChunk.id, isouter=True)
        .where(KbChunk.knowledge_base_id == knowledge_base_id)
        .order_by(KbChunk.created_at.desc(), KbChunk.chunk_index.asc())
    )
    chunks = []
    for chunk, embedding in result.all():
        chunks.append(
            {
                "id": str(chunk.id),
                "title": chunk.title,
                "sourceType": chunk.source.source_type if chunk.source else None,
                "sourceId": str(chunk.source_id),
                "content": chunk.content,
                "metadata": chunk.metadata_ or {},
                "embedding": embedding,
            }
        )
    return chunks


@router.get("", response_model=dict)
async def list_knowledge_bases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(KbKnowledgeBase)
        .where(KbKnowledgeBase.workspace_id == workspace.id)
        .order_by(KbKnowledgeBase.updated_at.desc())
    )
    items = []
    for item in result.scalars().all():
        items.append(await _knowledge_payload(db, item))
    return {"success": True, "data": items}


@router.post("", response_model=dict)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库名称不能为空")
    item = KbKnowledgeBase(
        workspace_id=workspace.id,
        name=name,
        description=payload.description or "",
        visibility=payload.visibility,
        user_id=user.id,
    )
    db.add(item)
    await db.flush()
    return {"success": True, "data": await _knowledge_payload(db, item)}


@router.get("/{knowledge_base_id}", response_model=dict)
async def get_knowledge_base(
    knowledge_base_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
    return {"success": True, "data": await _knowledge_payload(db, item)}


@router.patch("/{knowledge_base_id}", response_model=dict)
async def update_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)

    if payload.name is not None:
        item.name = payload.name.strip() or item.name
    if payload.description is not None:
        item.description = payload.description
    if payload.visibility is not None:
        item.visibility = payload.visibility
    await db.flush()
    return {"success": True, "data": await _knowledge_payload(db, item)}


@router.delete("/{knowledge_base_id}", response_model=dict)
async def delete_knowledge_base(
    knowledge_base_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)

    # Clean up chunks and embeddings
    chunk_result = await db.execute(
        select(KbChunk.id).where(KbChunk.knowledge_base_id == item.id)
    )
    chunk_ids = [row[0] for row in chunk_result.all()]
    if chunk_ids:
        await db.execute(delete(KbChunkEmbedding).where(KbChunkEmbedding.chunk_id.in_(chunk_ids)))
        await db.execute(delete(KbChunk).where(KbChunk.id.in_(chunk_ids)))

    # Clean up sources
    await db.execute(delete(KbSource).where(KbSource.knowledge_base_id == item.id))

    # Delete the knowledge base
    await db.delete(item)
    await db.flush()

    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="knowledge.deleted",
            resource_type="knowledge_base",
            resource_id=item.id,
            meta={"name": item.name},
        )
    )
    await db.flush()
    return {"success": True, "data": None}


@router.get("/{knowledge_base_id}/settings", response_model=dict)
async def get_knowledge_settings(
    knowledge_base_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
    return {"success": True, "data": await _knowledge_payload(db, item)}


@router.post("/{knowledge_base_id}/sources", response_model=dict)
async def add_knowledge_source(
    knowledge_base_id: str,
    payload: KnowledgeSourceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    try:
        workspace = await ensure_user_workspace(db, user)
        item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
        source_uuid = None
        # Only validate UUID for file/document types
        if payload.source_type in {"file", "document"}:
            if not payload.source_id:
                raise HTTPException(status_code=400, detail=f"{payload.source_type} 类型必须提供 source_id")
            source_uuid = _uuid_or_400(payload.source_id, "source_id")
        elif payload.source_type in {"link", "text", "manual"}:
            # For these types, source_id carries the actual content (URL, text, manual title+body)
            pass

        index_meta = {}
        sync_status = "pending"
        title = (payload.title or payload.source_id or payload.source_type)[:255]
        file_id = None
        document_id = None
        url = None

        if source_uuid:
            if payload.source_type == "file":
                file_id = source_uuid
            elif payload.source_type == "document":
                document_id = source_uuid
        elif payload.source_type == "link":
            url = payload.source_id

        source = KbSource(
            knowledge_base_id=item.id,
            user_id=user.id,
            title=title,
            source_type=payload.source_type,
            file_id=file_id,
            document_id=document_id,
            url=url,
            status=sync_status,
            metadata_=index_meta,
        )
        db.add(source)
        await db.flush()

        # Index file/document sources
        if source_uuid and payload.source_type in {"file", "document"}:
            try:
                index_meta = await _index_source(
                    db,
                    workspace_id=workspace.id,
                    knowledge_base_id=item.id,
                    source_type=payload.source_type,
                    source_id=source_uuid,
                    source_record_id=source.id,
                )
                source.status = "synced"
                source.metadata_ = index_meta
                source.chunk_count = index_meta.get("chunkCount", 0)
                item.source_count = (item.source_count or 0) + 1
                item.chunk_count = (item.chunk_count or 0) + index_meta.get("chunkCount", 0)
            except Exception as exc:
                source.status = "failed"
                source.error_message = str(exc)

        # Index text/manual sources directly from submitted content
        elif payload.source_type in {"text", "manual"} and payload.source_id:
            try:
                text_content = payload.source_id
                # This is wrapped in try/except below
                # Strip HTML for text indexing
                from html.parser import HTMLParser
                class HTMLStripper(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.text = []
                    def handle_data(self, data):
                        self.text.append(data)
                stripper = HTMLStripper()
                try:
                    stripper.feed(text_content)
                    plain_data = "".join(stripper.text)
                except Exception:
                    plain_data = text_content

                source.raw_text = text_content
                chunks = build_chunks(plain_data, source_title=title)
                for chunk_data in chunks:
                    chunk_id = uuid.uuid4()
                    content = str(chunk_data["content"])
                    chunk = KbChunk(
                        id=chunk_id,
                        knowledge_base_id=item.id,
                        source_id=source.id,
                        title=title,
                        chunk_index=int(chunk_data["chunk_index"]),
                        content=content,
                        content_hash=None,
                        token_count=0,
                        char_count=len(content),
                        metadata_=chunk_data.get("metadata", {}),
                    )
                    embedding = KbChunkEmbedding(
                        chunk_id=chunk_id,
                        embedding_model_name=embedding_model_name(),
                        embedding=embed_text(content),
                    )
                    db.add(chunk)
                    db.add(embedding)
                source.status = "synced"
                source.chunk_count = len(chunks)
                source.metadata_ = {"title": title, "chunkCount": len(chunks), "characters": len(plain_data)}
                item.source_count = (item.source_count or 0) + 1
                item.chunk_count = (item.chunk_count or 0) + len(chunks)
            except Exception as exc:
                source.status = "failed"
                source.error_message = str(exc)

            except Exception as exc:
                source.status = "failed"
                source.error_message = f"处理内容失败: {str(exc)}"

        elif payload.source_type == "link" and url:
            source.status = "synced"
            source.metadata_ = {"url": url}
            item.source_count = (item.source_count or 0) + 1
        db.add(
            AuditLog(
                workspace_id=workspace.id,
                user_id=user.id,
                action="knowledge.source.add",
                resource_type="knowledge_base",
                resource_id=item.id,
                meta={"sourceType": payload.source_type, "sourceId": str(source_uuid) if source_uuid else None, **index_meta},
            )
        )
        await db.flush()
        return {"success": True, "data": _source_payload(source)}


    except HTTPException: raise
    except Exception as exc:
        import traceback, logging
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(exc)}") from exc
@router.get("/{knowledge_base_id}/sources", response_model=dict)
async def list_knowledge_sources(
    knowledge_base_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
    result = await db.execute(
        select(KbSource)
        .where(KbSource.knowledge_base_id == item.id)
        .order_by(KbSource.created_at.desc())
    )
    return {"success": True, "data": [_source_payload(source) for source in result.scalars().all()]}


@router.delete("/{knowledge_base_id}/sources/{source_id}", response_model=dict)
async def delete_knowledge_source(
    knowledge_base_id: str,
    source_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
    source_uuid = uuid.UUID(source_id)
    result = await db.execute(
        select(KbSource).where(
            KbSource.id == source_uuid,
            KbSource.knowledge_base_id == item.id,
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="资料来源未找到")

    # Clean up associated chunks and embeddings
    chunk_result = await db.execute(
        select(KbChunk.id).where(KbChunk.source_id == source.id)
    )
    chunk_ids = [row[0] for row in chunk_result.all()]
    if chunk_ids:
        await db.execute(delete(KbChunkEmbedding).where(KbChunkEmbedding.chunk_id.in_(chunk_ids)))
        await db.execute(delete(KbChunk).where(KbChunk.id.in_(chunk_ids)))

    # Update knowledge base counters
    item.source_count = max(0, (item.source_count or 1) - 1)
    item.chunk_count = max(0, (item.chunk_count or 0) - len(chunk_ids))

    await db.delete(source)
    await db.flush()
    return {"success": True, "data": None}


@router.post("/{knowledge_base_id}/ask", response_model=dict)
async def ask_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeAskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
    chunks = await _load_kb_chunks(db, knowledge_base_id=item.id)
    ranked = rank_chunks(payload.question, chunks, limit=payload.limit)
    answer = answer_question(payload.question, ranked)
    await assert_ai_quota(
        db,
        workspace,
        estimated_tokens=max(1, (len(payload.question) + len(answer)) // 4),
        request_count=1,
    )

    conversation = AIConversation(
        workspace_id=workspace.id,
        user_id=user.id,
        title=f"{item.name} 知识库问答",
        source_type="knowledge_base",
        source_id=item.id,
    )
    db.add(conversation)
    await db.flush()
    db.add(AIMessage(conversation_id=conversation.id, role="user", content=payload.question, meta={"source": "knowledge"}))
    db.add(
        AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            model_provider="local",
            model_name="local-retrieval",
            input_tokens=max(1, len(payload.question) // 4),
            output_tokens=max(1, len(answer) // 4),
            meta={"sources": ranked},
        )
    )
    db.add(
        UsageRecord(
            workspace_id=workspace.id,
            user_id=user.id,
            usage_type="ai_tokens",
            quantity=Decimal(max(1, (len(payload.question) + len(answer)) // 4)),
            unit="tokens",
            model_name="local-retrieval",
            cost=Decimal("0"),
            meta={"knowledgeBaseId": str(item.id), "conversationId": str(conversation.id), "mode": "knowledge_ask"},
        )
    )
    await db.flush()
    return {
        "success": True,
        "data": {
            "answer": answer,
            "conversationId": str(conversation.id),
            "sources": ranked,
        },
    }


@router.post("/{knowledge_base_id}/sync", response_model=dict)
async def sync_knowledge_base(
    knowledge_base_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_knowledge_in_workspace(db, workspace.id, knowledge_base_id)
    result = await db.execute(
        select(KbSource).where(KbSource.knowledge_base_id == item.id).order_by(KbSource.created_at.asc())
    )
    sources = result.scalars().all()
    synced = []
    failed = []
    for source in sources:
        # Determine external source identifier
        ext_source_id = source.file_id or source.document_id
        if source.url:
            try:
                ext_source_id = uuid.UUID(source.url) if source.url else None
            except (ValueError, AttributeError):
                ext_source_id = None

        if ext_source_id is None:
            source.status = "skipped"
            continue
        try:
            meta = await _index_source(
                db,
                workspace_id=workspace.id,
                knowledge_base_id=item.id,
                source_type=source.source_type,
                source_id=ext_source_id,
                source_record_id=source.id,
            )
            source.status = "synced"
            source.metadata_ = meta
            source.chunk_count = meta.get("chunkCount", 0)
            synced.append({"sourceId": str(source.id), **meta})
        except Exception as exc:
            source.status = "failed"
            source.metadata_ = {**(source.metadata_ or {}), "error": str(exc)}
            failed.append({"sourceId": str(source.id), "error": str(exc)})
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="knowledge.sync",
            resource_type="knowledge_base",
            resource_id=item.id,
            meta={"synced": len(synced), "failed": len(failed)},
        )
    )
    await db.flush()
    return {"success": True, "data": {"synced": synced, "failed": failed, "sourceCount": len(sources)}}
