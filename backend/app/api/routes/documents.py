from __future__ import annotations

import io
import json
import secrets
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.ai import AIConversation, AIMessage
from app.models.document import Document, DocumentShare, DocumentVersion
from app.models.knowledge import KbChunk, KbChunkEmbedding, KbKnowledgeBase, KbSource
from app.models.operations import AuditLog, UsageRecord
from app.models.user import User
from app.services.billing import assert_ai_quota
from app.services.bootstrap import ensure_user_workspace
from app.services.file_ai import build_chunks, embed_text, embedding_model_name, summarize_text

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    title: str = Field(default="未命名文档", max_length=255)
    content: dict = Field(default_factory=dict)
    content_text: str = ""
    folder_id: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: dict | None = None
    content_text: str | None = None
    status: str | None = None


class DocumentAIWriteRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=2000)
    mode: str = Field(default="draft", pattern="^(draft|summary|rewrite|outline|continue)$")
    apply: bool = False


class DocumentKnowledgeRequest(BaseModel):
    knowledge_base_id: str = Field(..., min_length=1)


class ShareCreate(BaseModel):
    share_type: str = Field(default="link", pattern="^(link|workspace|team)$")
    permission: str = Field(default="view", pattern="^(view|comment|edit)$")


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 鏃犳晥") from exc


def _document_payload(item: Document):
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "ownerId": str(item.owner_id) if item.owner_id else None,
        "folderId": str(item.folder_id) if item.folder_id else None,
        "title": item.title,
        "content": item.content or {},
        "contentText": item.content_text,
        "status": item.status,
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


def _share_payload(item: DocumentShare):
    return {
        "id": str(item.id),
        "documentId": str(item.document_id),
        "shareType": item.share_type,
        "permission": item.permission,
        "token": item.token,
        "shareUrl": f"/share/documents/{item.token}" if item.token else None,
        "expiresAt": _dt(item.expires_at),
        "createdBy": str(item.created_by) if item.created_by else None,
        "createdAt": _dt(item.created_at),
    }


async def _next_version_no(db: AsyncSession, document_id: uuid.UUID) -> int:
    current = await db.scalar(
        select(func.coalesce(func.max(DocumentVersion.version_no), 0)).where(
            DocumentVersion.document_id == document_id
        )
    )
    return int(current or 0) + 1


async def _get_document_in_workspace(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    document_id: str,
) -> Document:
    document_uuid = _uuid_or_400(document_id)
    result = await db.execute(
        select(Document).where(
            Document.id == document_uuid,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return item


async def _get_document_share(db: AsyncSession, workspace_id: uuid.UUID, share_id: str) -> DocumentShare:
    share_uuid = _uuid_or_400(share_id, "share_id")
    result = await db.execute(
        select(DocumentShare)
        .join(Document, Document.id == DocumentShare.document_id)
        .where(
            DocumentShare.id == share_uuid,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="分享记录不存在")
    return item


def _document_bytes(item: Document, export_format: str) -> tuple[bytes, str, str]:
    safe_title = item.title.strip() or "document"
    text = item.content_text or ""
    if export_format == "json":
        data = {
            "id": str(item.id),
            "title": item.title,
            "content": item.content or {},
            "contentText": text,
            "updatedAt": _dt(item.updated_at),
        }
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"), f"{safe_title}.json", "application/json"
    if export_format == "txt":
        return text.encode("utf-8-sig"), f"{safe_title}.txt", "text/plain; charset=utf-8"
    body = f"# {item.title}\n\n{text}".strip() + "\n"
    return body.encode("utf-8"), f"{safe_title}.md", "text/markdown; charset=utf-8"


def _build_ai_text(item: Document, payload: DocumentAIWriteRequest) -> str:
    base = (item.content_text or "").strip()
    if payload.mode == "summary":
        return f"## 文档摘要\n\n{summarize_text(base or payload.instruction)}"
    if payload.mode == "outline":
        seed = base or payload.instruction
        lines = [line.strip(" -#") for line in seed.splitlines() if line.strip()]
        points = lines[:6] or [payload.instruction]
        return "## 建议大纲\n\n" + "\n".join(f"{index + 1}. {point}" for index, point in enumerate(points))
    if payload.mode == "continue":
        seed = base or payload.instruction
        return (
            "## 续写内容\n\n"
            f"基于当前文档继续展开：{payload.instruction}\n\n"
            f"{summarize_text(seed, max_sentences=2)}\n\n"
            "### 下一步展开\n"
            "1. 补充背景、目标和关键约束。\n"
            "2. 梳理执行步骤、负责人和交付物。\n"
            "3. 给出风险提示和后续行动清单。\n"
        )
    if payload.mode == "rewrite":
        return (
            "## 改写版本\n\n"
            f"改写要求：{payload.instruction}\n\n"
            f"{base or '请先补充原始内容，序光会继续根据你的要求进行扩写和润色。'}"
        )
    return (
        "## AI 起草内容\n\n"
        f"主题：{payload.instruction}\n\n"
        "### 背景\n"
        f"{summarize_text(base, max_sentences=2) if base else '这里用于补充任务背景、目标对象和关键约束。'}\n\n"
        "### 核心内容\n"
        "1. 明确目标和交付范围。\n"
        "2. 梳理相关资料、文件和知识库来源。\n"
        "3. 输出行动项、负责人和下一步计划。\n"
    )


async def _add_document_to_knowledge(
    db: AsyncSession,
    *,
    item: Document,
    knowledge_base: KbKnowledgeBase,
    user_id: uuid.UUID,
) -> dict:
    # Find or create the knowledge source record first
    source_result = await db.execute(
        select(KbSource).where(
            KbSource.knowledge_base_id == knowledge_base.id,
            KbSource.source_type == "document",
            KbSource.document_id == item.id,
        )
    )
    source = source_result.scalar_one_or_none()
    if source is None:
        source = KbSource(
            knowledge_base_id=knowledge_base.id,
            user_id=user_id,
            source_type="document",
            title=item.title,
            document_id=item.id,
            status="pending",
            metadata_={"title": item.title},
        )
        db.add(source)
        await db.flush()
    else:
        source.status = "pending"
        source.metadata_ = {"title": item.title}

    # Clear old chunks for this source
    chunk_result = await db.execute(
        select(KbChunk.id).where(
            KbChunk.knowledge_base_id == knowledge_base.id,
            KbChunk.source_id == source.id,
        )
    )
    chunk_ids = [row[0] for row in chunk_result.all()]
    if chunk_ids:
        await db.execute(
            delete(KbChunkEmbedding).where(KbChunkEmbedding.chunk_id.in_(chunk_ids))
        )
        await db.execute(delete(KbChunk).where(KbChunk.id.in_(chunk_ids)))

    chunks = build_chunks(item.content_text or item.title, source_title=item.title)
    for chunk_data in chunks:
        chunk_id = uuid.uuid4()
        chunk = KbChunk(
            id=chunk_id,
            knowledge_base_id=knowledge_base.id,
            source_id=source.id,
            title=item.title,
            chunk_index=int(chunk_data["chunk_index"]),
            content=str(chunk_data["content"]),
            content_hash=None,
            token_count=0,
            char_count=len(str(chunk_data["content"])),
            metadata_=chunk_data.get("metadata", {}),
        )
        embedding = KbChunkEmbedding(
            chunk_id=chunk_id,
            embedding_model_name=embedding_model_name(),
            embedding=embed_text(chunk.content),
        )
        db.add(chunk)
        db.add(embedding)

    source.status = "synced"
    source.metadata_ = {"title": item.title, "chunkCount": len(chunks)}
    source.chunk_count = len(chunks)
    knowledge_base.source_count = (knowledge_base.source_count or 0) + 1
    knowledge_base.chunk_count = (knowledge_base.chunk_count or 0) + len(chunks)

    db.add(
        AuditLog(
            workspace_id=item.workspace_id,
            user_id=user_id,
            action="document.add_to_knowledge",
            resource_type="document",
            resource_id=item.id,
            meta={"knowledgeBaseId": str(knowledge_base.id), "chunkCount": len(chunks)},
        )
    )
    await db.flush()
    return {"knowledgeBaseId": str(knowledge_base.id), "sourceId": str(source.id), "chunkCount": len(chunks)}


@router.get("", response_model=dict)
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace.id, Document.deleted_at.is_(None))
        .order_by(Document.updated_at.desc())
    )
    return {"success": True, "data": [_document_payload(item) for item in result.scalars().all()]}


@router.post("", response_model=dict)
async def create_document(
    payload: DocumentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    folder_uuid = _uuid_or_400(payload.folder_id, "folder_id") if payload.folder_id else None
    title = payload.title.strip() or "未命名文档"
    item = Document(
        workspace_id=workspace.id,
        owner_id=user.id,
        folder_id=folder_uuid,
        title=title,
        content=payload.content,
        content_text=payload.content_text,
        status="draft",
    )
    db.add(item)
    await db.flush()
    db.add(
        DocumentVersion(
            document_id=item.id,
            version_no=1,
            content=item.content,
            content_text=item.content_text,
            created_by=user.id,
        )
    )
    return {"success": True, "data": _document_payload(item)}


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    return {"success": True, "data": _document_payload(item)}


@router.patch("/{document_id}", response_model=dict)
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)

    if payload.title is not None:
        item.title = payload.title.strip() or item.title
    if payload.content is not None:
        item.content = payload.content
    if payload.content_text is not None:
        item.content_text = payload.content_text
    if payload.status is not None:
        item.status = payload.status

    version_no = await _next_version_no(db, item.id)
    db.add(
        DocumentVersion(
            document_id=item.id,
            version_no=version_no,
            content=item.content,
            content_text=item.content_text,
            created_by=user.id,
        )
    )
    await db.flush()
    return {"success": True, "data": _document_payload(item)}


@router.get("/{document_id}/versions", response_model=dict)
async def list_document_versions(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == item.id)
        .order_by(DocumentVersion.version_no.desc())
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(version.id),
                "documentId": str(version.document_id),
                "versionNo": version.version_no,
                "contentText": version.content_text,
                "createdBy": str(version.created_by) if version.created_by else None,
                "createdAt": _dt(version.created_at),
            }
            for version in result.scalars().all()
        ],
    }


@router.get("/{document_id}/export")
async def export_document(
    document_id: str,
    format: str = "md",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    export_format = format.lower()
    if export_format not in {"md", "txt", "json"}:
        raise HTTPException(status_code=400, detail="暂不支持该导出格式")
    data, filename, media_type = _document_bytes(item, export_format)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return StreamingResponse(io.BytesIO(data), media_type=media_type, headers=headers)


@router.get("/{document_id}/shares", response_model=dict)
async def list_document_shares(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    result = await db.execute(
        select(DocumentShare).where(DocumentShare.document_id == item.id).order_by(DocumentShare.created_at.desc())
    )
    return {"success": True, "data": [_share_payload(share) for share in result.scalars().all()]}


@router.post("/{document_id}/shares", response_model=dict)
async def create_document_share(
    document_id: str,
    payload: ShareCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    share = DocumentShare(
        document_id=item.id,
        share_type=payload.share_type,
        permission=payload.permission,
        token=secrets.token_urlsafe(24),
        created_by=user.id,
    )
    db.add(share)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="document.share.create",
            resource_type="document",
            resource_id=item.id,
            meta={"shareType": payload.share_type, "permission": payload.permission},
        )
    )
    await db.flush()
    return {"success": True, "data": _share_payload(share)}


@router.delete("/shares/{share_id}", response_model=dict)
async def delete_document_share(
    share_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    share = await _get_document_share(db, workspace.id, share_id)
    document_id = share.document_id
    await db.delete(share)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="document.share.delete",
            resource_type="document",
            resource_id=document_id,
            meta={"shareId": share_id},
        )
    )
    return {"success": True}


@router.post("/{document_id}/ai-write", response_model=dict)
async def ai_write_document(
    document_id: str,
    payload: DocumentAIWriteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    generated = _build_ai_text(item, payload)
    await assert_ai_quota(
        db,
        workspace,
        estimated_tokens=max(1, (len(payload.instruction) + len(generated)) // 4),
        request_count=1,
    )
    if payload.apply:
        item.content_text = f"{item.content_text.rstrip()}\n\n{generated}".strip()
        item.content = {"type": "plain_text", "updatedAt": datetime.now(UTC).isoformat()}
        version_no = await _next_version_no(db, item.id)
        db.add(
            DocumentVersion(
                document_id=item.id,
                version_no=version_no,
                content=item.content,
                content_text=item.content_text,
                created_by=user.id,
            )
        )

    conversation = AIConversation(
        workspace_id=workspace.id,
        user_id=user.id,
        title=f"{item.title} AI 鍐欎綔",
        source_type="document",
        source_id=item.id,
    )
    db.add(conversation)
    await db.flush()
    db.add(AIMessage(conversation_id=conversation.id, role="user", content=payload.instruction, meta={"mode": payload.mode}))
    db.add(
        AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=generated,
            model_provider="local",
            model_name="local-document-writer",
            input_tokens=max(1, len(payload.instruction) // 4),
            output_tokens=max(1, len(generated) // 4),
            meta={"applied": payload.apply},
        )
    )
    db.add(
        UsageRecord(
            workspace_id=workspace.id,
            user_id=user.id,
            usage_type="ai_tokens",
            quantity=Decimal(max(1, (len(payload.instruction) + len(generated)) // 4)),
            unit="tokens",
            model_name="local-document-writer",
            cost=Decimal("0"),
            meta={"documentId": str(item.id), "conversationId": str(conversation.id), "mode": payload.mode},
        )
    )
    await db.flush()
    return {
        "success": True,
        "data": {
            "generated": generated,
            "conversationId": str(conversation.id),
            "document": _document_payload(item),
        },
    }


@router.post("/{document_id}/knowledge", response_model=dict)
async def add_document_to_knowledge(
    document_id: str,
    payload: DocumentKnowledgeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    kb_uuid = _uuid_or_400(payload.knowledge_base_id, "knowledge_base_id")
    result = await db.execute(
        select(KbKnowledgeBase).where(KbKnowledgeBase.id == kb_uuid, KbKnowledgeBase.workspace_id == workspace.id)
    )
    knowledge_base = result.scalar_one_or_none()
    if knowledge_base is None:
        raise HTTPException(status_code=404, detail="知识库不存在")
    data = await _add_document_to_knowledge(db, item=item, knowledge_base=knowledge_base, user_id=user.id)
    return {"success": True, "data": data}


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_document_in_workspace(db, workspace.id, document_id)
    item.deleted_at = datetime.now(UTC)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="document.delete",
            resource_type="document",
            resource_id=item.id,
            meta={"title": item.title},
        )
    )
    await db.flush()
    return {"success": True}

