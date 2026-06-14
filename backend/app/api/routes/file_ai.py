from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.database import AsyncSessionLocal
from app.api.routes.auth import get_current_user
from app.models.ai import AIConversation, AIMessage
from app.models.drive import WorkspaceFile
from app.models.knowledge import FileChunk, FileEmbedding, KnowledgeBase
from app.models.operations import AuditLog, Job, UsageRecord
from app.models.user import User
from app.models.workspace import Workspace
from app.services.billing import assert_ai_quota, assert_storage_quota
from app.services.bootstrap import ensure_user_workspace
from app.services.file_ai import (
    answer_question,
    build_chunks,
    clean_table,
    embed_text,
    embedding_model_name,
    merge_tables,
    parse_file_bytes,
    parse_table_bytes,
    rank_chunks,
    split_table,
    summarize_text,
    table_to_csv_bytes,
)
from app.services.storage import get_storage
from app.utils.files import new_storage_key, secure_filename

router = APIRouter(prefix="/file-ai", tags=["file-ai"])


class FileAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=12)


class FileSplitRequest(BaseModel):
    column: str | None = Field(default=None, max_length=160)
    rows_per_file: int | None = Field(default=None, ge=1, le=100000)


class FileMergeRequest(BaseModel):
    file_ids: list[str] = Field(..., min_length=2, max_length=50)
    output_name: str = Field(default="merged.csv", max_length=180)


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


def _file_payload(item: WorkspaceFile):
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "folderId": str(item.folder_id) if item.folder_id else None,
        "name": item.name,
        "extension": item.extension,
        "mimeType": item.mime_type,
        "size": item.size,
        "storageKey": item.storage_key,
        "status": item.status,
        "parseStatus": item.parse_status,
        "aiStatus": item.ai_status,
        "metadata": item.meta or {},
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


def _job_payload(item: Job):
    return {
        "id": str(item.id),
        "type": item.type,
        "status": item.status,
        "progress": item.progress,
        "input": item.input or {},
        "output": item.output or {},
        "errorMessage": item.error_message,
        "createdAt": _dt(item.created_at),
        "startedAt": _dt(item.started_at),
        "finishedAt": _dt(item.finished_at),
    }


async def _get_workspace_file(db: AsyncSession, workspace_id: uuid.UUID, file_id: str) -> WorkspaceFile:
    file_uuid = _uuid_or_400(file_id, "file_id")
    result = await db.execute(
        select(WorkspaceFile).where(
            WorkspaceFile.id == file_uuid,
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return item


async def _read_workspace_file(item: WorkspaceFile) -> bytes:
    storage = get_storage()
    if not await storage.exists(item.storage_key):
        raise HTTPException(status_code=404, detail="文件内容不存在")
    return await storage.read(item.storage_key)


async def _write_workspace_file(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    data: bytes,
    mime_type: str,
    meta: dict,
) -> WorkspaceFile:
    clean_name = secure_filename(filename.strip()) or f"result-{uuid.uuid4().hex[:8]}.csv"
    workspace = await db.get(Workspace, workspace_id)
    if workspace:
        await assert_storage_quota(db, workspace, len(data))
    storage_key, _ = new_storage_key(clean_name, prefix=f"workspaces/{workspace_id}/drive")
    await get_storage().save(storage_key, data)
    ext = Path(clean_name).suffix.lower().lstrip(".")
    item = WorkspaceFile(
        workspace_id=workspace_id,
        owner_id=user_id,
        name=clean_name,
        extension=ext,
        mime_type=mime_type,
        size=len(data),
        storage_provider="local",
        storage_key=storage_key,
        parse_status="pending",
        ai_status="not_ready",
        meta=meta,
    )
    db.add(item)
    await db.flush()
    return item


def _create_job(
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    job_type: str,
    job_input: dict,
    output: dict,
    status: str = "success",
) -> Job:
    now = datetime.now(UTC)
    return Job(
        workspace_id=workspace_id,
        user_id=user_id,
        type=job_type,
        status=status,
        progress=100 if status == "success" else 0,
        input=job_input,
        output=output,
        started_at=now,
        finished_at=now if status in {"success", "failed", "cancelled"} else None,
    )


def _usage(
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    usage_type: str,
    quantity: int,
    unit: str,
    meta: dict,
) -> UsageRecord:
    return UsageRecord(
        workspace_id=workspace_id,
        user_id=user_id,
        usage_type=usage_type,
        quantity=Decimal(quantity),
        unit=unit,
        model_name="local-deterministic",
        cost=Decimal("0"),
        meta=meta,
    )


def _audit(
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None,
    meta: dict,
) -> AuditLog:
    return AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta,
    )


async def _clear_existing_chunks(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    knowledge_base_id: uuid.UUID | None = None,
) -> None:
    embedding_stmt = delete(FileEmbedding).where(
        FileEmbedding.workspace_id == workspace_id,
        FileEmbedding.source_type == source_type,
        FileEmbedding.source_id == source_id,
    )
    chunk_stmt = delete(FileChunk).where(
        FileChunk.workspace_id == workspace_id,
        FileChunk.source_type == source_type,
        FileChunk.source_id == source_id,
    )
    if knowledge_base_id:
        embedding_stmt = embedding_stmt.where(FileEmbedding.knowledge_base_id == knowledge_base_id)
        chunk_stmt = chunk_stmt.where(FileChunk.knowledge_base_id == knowledge_base_id)
    else:
        embedding_stmt = embedding_stmt.where(FileEmbedding.knowledge_base_id.is_(None))
        chunk_stmt = chunk_stmt.where(FileChunk.knowledge_base_id.is_(None))
    await db.execute(embedding_stmt)
    await db.execute(chunk_stmt)


async def _index_file(
    db: AsyncSession,
    *,
    item: WorkspaceFile,
    user_id: uuid.UUID,
    knowledge_base_id: uuid.UUID | None = None,
) -> dict:
    data = await _read_workspace_file(item)
    parsed = parse_file_bytes(item.name, item.extension, data)
    chunks = build_chunks(parsed.text, source_title=item.name)
    workspace = await db.get(Workspace, item.workspace_id)
    if workspace:
        await assert_ai_quota(db, workspace, estimated_tokens=max(1, len(parsed.text) // 4), request_count=1)
    await _clear_existing_chunks(
        db,
        workspace_id=item.workspace_id,
        source_type="file",
        source_id=item.id,
        knowledge_base_id=knowledge_base_id,
    )

    for chunk_data in chunks:
        chunk_id = uuid.uuid4()
        chunk = FileChunk(
            id=chunk_id,
            workspace_id=item.workspace_id,
            file_id=item.id,
            knowledge_base_id=knowledge_base_id,
            source_type="file",
            source_id=item.id,
            title=item.name,
            chunk_index=int(chunk_data["chunk_index"]),
            content=str(chunk_data["content"]),
            content_type="text",
            meta=chunk_data["metadata"],
        )
        embedding = FileEmbedding(
            workspace_id=item.workspace_id,
            file_id=item.id,
            knowledge_base_id=knowledge_base_id,
            source_type="file",
            source_id=item.id,
            chunk_id=chunk_id,
            embedding_model=embedding_model_name(),
            embedding=embed_text(chunk.content),
        )
        db.add(chunk)
        db.add(embedding)

    item.parse_status = "parsed" if chunks else "empty"
    item.ai_status = "ready" if chunks else "empty"
    item.meta = {
        **(item.meta or {}),
        "parser": parsed.parser,
        "parseMetadata": parsed.metadata,
        "chunkCount": len(chunks),
        "indexedAt": datetime.now(UTC).isoformat(),
    }

    job = _create_job(
        workspace_id=item.workspace_id,
        user_id=user_id,
        job_type="file_index",
        job_input={"fileId": str(item.id), "knowledgeBaseId": str(knowledge_base_id) if knowledge_base_id else None},
        output={"chunkCount": len(chunks), "parser": parsed.parser, "characters": len(parsed.text)},
    )
    db.add(job)
    db.add(
        _usage(
            workspace_id=item.workspace_id,
            user_id=user_id,
            usage_type="embedding_tokens",
            quantity=max(1, len(parsed.text) // 4) if parsed.text else 0,
            unit="tokens",
            meta={"fileId": str(item.id), "chunkCount": len(chunks)},
        )
    )
    db.add(
        _audit(
            workspace_id=item.workspace_id,
            user_id=user_id,
            action="file.index",
            resource_type="file",
            resource_id=item.id,
            meta={"chunkCount": len(chunks), "knowledgeBaseId": str(knowledge_base_id) if knowledge_base_id else None},
        )
    )
    await db.flush()
    return {"file": _file_payload(item), "job": _job_payload(job), "chunkCount": len(chunks), "parser": parsed.parser}


async def _load_rankable_chunks(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    file_id: uuid.UUID | None = None,
    knowledge_base_id: uuid.UUID | None = None,
) -> list[dict]:
    stmt = (
        select(FileChunk, FileEmbedding.embedding)
        .join(FileEmbedding, FileEmbedding.chunk_id == FileChunk.id, isouter=True)
        .where(FileChunk.workspace_id == workspace_id)
        .order_by(FileChunk.chunk_index.asc())
    )
    if file_id:
        stmt = stmt.where(FileChunk.file_id == file_id)
    if knowledge_base_id:
        stmt = stmt.where(FileChunk.knowledge_base_id == knowledge_base_id)
    result = await db.execute(stmt)
    items = []
    for chunk, embedding in result.all():
        items.append(
            {
                "id": str(chunk.id),
                "fileId": str(chunk.file_id) if chunk.file_id else None,
                "knowledgeBaseId": str(chunk.knowledge_base_id) if chunk.knowledge_base_id else None,
                "sourceType": chunk.source_type,
                "sourceId": str(chunk.source_id) if chunk.source_id else None,
                "title": chunk.title,
                "content": chunk.content,
                "metadata": chunk.meta or {},
                "embedding": embedding,
            }
        )
    return items


@router.post("/files/{file_id}/index", response_model=dict)
async def index_file(
    file_id: str,
    knowledge_base_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    kb_uuid = _uuid_or_400(knowledge_base_id, "knowledge_base_id") if knowledge_base_id else None
    if kb_uuid:
        kb = await db.scalar(select(KnowledgeBase.id).where(KnowledgeBase.id == kb_uuid, KnowledgeBase.workspace_id == workspace.id))
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")
    return {"success": True, "data": await _index_file(db, item=item, user_id=user.id, knowledge_base_id=kb_uuid)}


@router.post("/files/{file_id}/ask", response_model=dict)
async def ask_file(
    file_id: str,
    payload: FileAskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    chunks = await _load_rankable_chunks(db, workspace_id=workspace.id, file_id=item.id)
    if not chunks:
        await _index_file(db, item=item, user_id=user.id)
        chunks = await _load_rankable_chunks(db, workspace_id=workspace.id, file_id=item.id)
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
        title=f"{item.name} 问答",
        source_type="file",
        source_id=item.id,
    )
    db.add(conversation)
    await db.flush()
    db.add(AIMessage(conversation_id=conversation.id, role="user", content=payload.question, meta={"source": "file_ask"}))
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
        _usage(
            workspace_id=workspace.id,
            user_id=user.id,
            usage_type="ai_tokens",
            quantity=max(1, (len(payload.question) + len(answer)) // 4),
            unit="tokens",
            meta={"conversationId": str(conversation.id), "fileId": str(item.id), "mode": "file_ask"},
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


@router.post("/files/{file_id}/summarize", response_model=dict)
async def summarize_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    chunks = await _load_rankable_chunks(db, workspace_id=workspace.id, file_id=item.id)
    if not chunks:
        await _index_file(db, item=item, user_id=user.id)
        chunks = await _load_rankable_chunks(db, workspace_id=workspace.id, file_id=item.id)
    summary = summarize_text("\n\n".join(str(chunk["content"]) for chunk in chunks[:20]))
    await assert_ai_quota(db, workspace, estimated_tokens=max(1, len(summary) // 4), request_count=1)
    job = _create_job(
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="file_summary",
        job_input={"fileId": str(item.id)},
        output={"summary": summary, "fileId": str(item.id)},
    )
    db.add(job)
    db.add(
        _usage(
            workspace_id=workspace.id,
            user_id=user.id,
            usage_type="ai_tokens",
            quantity=max(1, len(summary) // 4),
            unit="tokens",
            meta={"fileId": str(item.id), "mode": "file_summary"},
        )
    )
    await db.flush()
    return {"success": True, "data": {"summary": summary, "job": _job_payload(job), "sources": chunks[:5]}}


@router.post("/files/{file_id}/excel/clean", response_model=dict)
async def clean_excel_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    table = parse_table_bytes(item.name, item.extension, await _read_workspace_file(item))
    cleaned = clean_table(table)
    output_name = f"{Path(item.name).stem}-cleaned.csv"
    output = await _write_workspace_file(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        filename=output_name,
        data=table_to_csv_bytes(cleaned),
        mime_type="text/csv",
        meta={"source": "excel_clean", "sourceFileId": str(item.id)},
    )
    job = _create_job(
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="excel_clean",
        job_input={"fileId": str(item.id)},
        output={"outputFileId": str(output.id), "rows": len(cleaned.rows)},
    )
    db.add(job)
    await db.flush()
    return {"success": True, "data": {"file": _file_payload(output), "job": _job_payload(job), "rows": len(cleaned.rows)}}


@router.post("/files/{file_id}/excel/split", response_model=dict)
async def split_excel_file(
    file_id: str,
    payload: FileSplitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    table = parse_table_bytes(item.name, item.extension, await _read_workspace_file(item))
    groups = split_table(table, column=payload.column, rows_per_file=payload.rows_per_file)
    created = []
    for suffix, split_data in groups.items():
        output = await _write_workspace_file(
            db,
            workspace_id=workspace.id,
            user_id=user.id,
            filename=f"{Path(item.name).stem}-{suffix}.csv",
            data=table_to_csv_bytes(split_data),
            mime_type="text/csv",
            meta={"source": "excel_split", "sourceFileId": str(item.id), "splitKey": suffix},
        )
        created.append(_file_payload(output))
    job = _create_job(
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="excel_split",
        job_input={"fileId": str(item.id), "column": payload.column, "rowsPerFile": payload.rows_per_file},
        output={"files": created, "fileCount": len(created)},
    )
    db.add(job)
    await db.flush()
    return {"success": True, "data": {"files": created, "job": _job_payload(job), "fileCount": len(created)}}


@router.post("/files/merge", response_model=dict)
async def merge_excel_files(
    payload: FileMergeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    files = [await _get_workspace_file(db, workspace.id, file_id) for file_id in payload.file_ids]
    tables = [parse_table_bytes(item.name, item.extension, await _read_workspace_file(item)) for item in files]
    merged = merge_tables(tables)
    output_name = payload.output_name if payload.output_name.lower().endswith(".csv") else f"{payload.output_name}.csv"
    output = await _write_workspace_file(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        filename=output_name,
        data=table_to_csv_bytes(merged),
        mime_type="text/csv",
        meta={"source": "excel_merge", "sourceFileIds": [str(item.id) for item in files]},
    )
    job = _create_job(
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="excel_merge",
        job_input={"fileIds": [str(item.id) for item in files]},
        output={"outputFileId": str(output.id), "rows": len(merged.rows)},
    )
    db.add(job)
    await db.flush()
    return {"success": True, "data": {"file": _file_payload(output), "job": _job_payload(job), "rows": len(merged.rows)}}


async def _create_pending_job(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    job_type: str,
    job_input: dict,
) -> Job:
    item = Job(
        workspace_id=workspace_id,
        user_id=user_id,
        type=job_type,
        status="pending",
        progress=0,
        input=job_input,
        output={},
    )
    db.add(item)
    await db.flush()
    return item


async def _run_file_ai_job(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if job is None:
            return
        job.status = "running"
        job.progress = 10
        job.started_at = datetime.now(UTC)
        await db.commit()

        try:
            payload = job.input or {}
            operation = str(payload.get("operation") or "")
            workspace_id = job.workspace_id
            user_id = job.user_id
            if workspace_id is None or user_id is None:
                raise RuntimeError("任务缺少工作空间或用户信息")

            output: dict
            if operation == "index":
                item = await _get_workspace_file(db, workspace_id, str(payload["fileId"]))
                kb_id = uuid.UUID(payload["knowledgeBaseId"]) if payload.get("knowledgeBaseId") else None
                output = await _index_file(db, item=item, user_id=user_id, knowledge_base_id=kb_id)
            elif operation == "ask":
                item = await _get_workspace_file(db, workspace_id, str(payload["fileId"]))
                chunks = await _load_rankable_chunks(db, workspace_id=workspace_id, file_id=item.id)
                if not chunks:
                    await _index_file(db, item=item, user_id=user_id)
                    chunks = await _load_rankable_chunks(db, workspace_id=workspace_id, file_id=item.id)
                question = str(payload["question"])
                ranked = rank_chunks(question, chunks, limit=int(payload.get("limit") or 5))
                answer = answer_question(question, ranked)
                output = {"answer": answer, "sources": ranked, "fileId": str(item.id)}
                db.add(
                    _usage(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        usage_type="ai_tokens",
                        quantity=max(1, (len(question) + len(answer)) // 4),
                        unit="tokens",
                        meta={"fileId": str(item.id), "mode": "file_ask_async"},
                    )
                )
            elif operation == "summarize":
                item = await _get_workspace_file(db, workspace_id, str(payload["fileId"]))
                chunks = await _load_rankable_chunks(db, workspace_id=workspace_id, file_id=item.id)
                if not chunks:
                    await _index_file(db, item=item, user_id=user_id)
                    chunks = await _load_rankable_chunks(db, workspace_id=workspace_id, file_id=item.id)
                summary = summarize_text("\n\n".join(str(chunk["content"]) for chunk in chunks[:20]))
                output = {"summary": summary, "sources": chunks[:5], "fileId": str(item.id)}
                db.add(
                    _usage(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        usage_type="ai_tokens",
                        quantity=max(1, len(summary) // 4),
                        unit="tokens",
                        meta={"fileId": str(item.id), "mode": "file_summary_async"},
                    )
                )
            elif operation == "clean":
                item = await _get_workspace_file(db, workspace_id, str(payload["fileId"]))
                table = parse_table_bytes(item.name, item.extension, await _read_workspace_file(item))
                cleaned = clean_table(table)
                output_file = await _write_workspace_file(
                    db,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    filename=f"{Path(item.name).stem}-cleaned.csv",
                    data=table_to_csv_bytes(cleaned),
                    mime_type="text/csv",
                    meta={"source": "table_clean_async", "sourceFileId": str(item.id)},
                )
                output = {"file": _file_payload(output_file), "rows": len(cleaned.rows)}
            elif operation == "split":
                item = await _get_workspace_file(db, workspace_id, str(payload["fileId"]))
                table = parse_table_bytes(item.name, item.extension, await _read_workspace_file(item))
                groups = split_table(
                    table,
                    column=payload.get("column"),
                    rows_per_file=payload.get("rowsPerFile"),
                )
                files = []
                for suffix, split_data in groups.items():
                    output_file = await _write_workspace_file(
                        db,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        filename=f"{Path(item.name).stem}-{suffix}.csv",
                        data=table_to_csv_bytes(split_data),
                        mime_type="text/csv",
                        meta={"source": "table_split_async", "sourceFileId": str(item.id), "splitKey": suffix},
                    )
                    files.append(_file_payload(output_file))
                output = {"files": files, "fileCount": len(files)}
            elif operation == "merge":
                file_ids = [str(value) for value in payload.get("fileIds", [])]
                files = [await _get_workspace_file(db, workspace_id, file_id) for file_id in file_ids]
                tables = [parse_table_bytes(item.name, item.extension, await _read_workspace_file(item)) for item in files]
                merged = merge_tables(tables)
                output_name = str(payload.get("outputName") or "merged.csv")
                if not output_name.lower().endswith(".csv"):
                    output_name = f"{output_name}.csv"
                output_file = await _write_workspace_file(
                    db,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    filename=output_name,
                    data=table_to_csv_bytes(merged),
                    mime_type="text/csv",
                    meta={"source": "table_merge_async", "sourceFileIds": file_ids},
                )
                output = {"file": _file_payload(output_file), "rows": len(merged.rows)}
            else:
                raise RuntimeError(f"未知文件 AI 任务: {operation}")

            job.status = "success"
            job.progress = 100
            job.output = output
            job.finished_at = datetime.now(UTC)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            async with AsyncSessionLocal() as error_db:
                error_job = await error_db.get(Job, job_id)
                if error_job is not None:
                    error_job.status = "failed"
                    error_job.progress = 100
                    error_job.error_message = str(exc)
                    error_job.finished_at = datetime.now(UTC)
                await error_db.commit()


@router.post("/files/{file_id}/index-async", response_model=dict)
async def index_file_async(
    file_id: str,
    background_tasks: BackgroundTasks,
    knowledge_base_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await _get_workspace_file(db, workspace.id, file_id)
    job = await _create_pending_job(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="file_index_async",
        job_input={"operation": "index", "fileId": file_id, "knowledgeBaseId": knowledge_base_id},
    )
    background_tasks.add_task(_run_file_ai_job, job.id)
    return {"success": True, "data": {"job": _job_payload(job)}}


@router.post("/files/{file_id}/ask-async", response_model=dict)
async def ask_file_async(
    file_id: str,
    payload: FileAskRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await _get_workspace_file(db, workspace.id, file_id)
    job = await _create_pending_job(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="file_ask_async",
        job_input={"operation": "ask", "fileId": file_id, "question": payload.question, "limit": payload.limit},
    )
    background_tasks.add_task(_run_file_ai_job, job.id)
    return {"success": True, "data": {"job": _job_payload(job)}}


@router.post("/files/{file_id}/summarize-async", response_model=dict)
async def summarize_file_async(
    file_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await _get_workspace_file(db, workspace.id, file_id)
    job = await _create_pending_job(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="file_summary_async",
        job_input={"operation": "summarize", "fileId": file_id},
    )
    background_tasks.add_task(_run_file_ai_job, job.id)
    return {"success": True, "data": {"job": _job_payload(job)}}


@router.post("/files/{file_id}/excel/clean-async", response_model=dict)
async def clean_excel_file_async(
    file_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await _get_workspace_file(db, workspace.id, file_id)
    job = await _create_pending_job(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="table_clean_async",
        job_input={"operation": "clean", "fileId": file_id},
    )
    background_tasks.add_task(_run_file_ai_job, job.id)
    return {"success": True, "data": {"job": _job_payload(job)}}


@router.post("/files/{file_id}/excel/split-async", response_model=dict)
async def split_excel_file_async(
    file_id: str,
    payload: FileSplitRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await _get_workspace_file(db, workspace.id, file_id)
    job = await _create_pending_job(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="table_split_async",
        job_input={
            "operation": "split",
            "fileId": file_id,
            "column": payload.column,
            "rowsPerFile": payload.rows_per_file,
        },
    )
    background_tasks.add_task(_run_file_ai_job, job.id)
    return {"success": True, "data": {"job": _job_payload(job)}}


@router.post("/files/merge-async", response_model=dict)
async def merge_excel_files_async(
    payload: FileMergeRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    for file_id in payload.file_ids:
        await _get_workspace_file(db, workspace.id, file_id)
    job = await _create_pending_job(
        db,
        workspace_id=workspace.id,
        user_id=user.id,
        job_type="table_merge_async",
        job_input={"operation": "merge", "fileIds": payload.file_ids, "outputName": payload.output_name},
    )
    background_tasks.add_task(_run_file_ai_job, job.id)
    return {"success": True, "data": {"job": _job_payload(job)}}
