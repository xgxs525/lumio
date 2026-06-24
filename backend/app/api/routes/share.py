from __future__ import annotations

import io
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.document import Document, DocumentShare
from app.models.drive import FileShare, WorkspaceFile
from app.services.storage import get_storage
from app.utils.files import download_content_disposition, safe_original_filename

router = APIRouter(prefix="/share", tags=["share"])


def _dt(value):
    return value.isoformat() if value else None


def _is_expired(value) -> bool:
    if value is None:
        return False
    now = datetime.now(UTC)
    expires_at = value if value.tzinfo else value.replace(tzinfo=UTC)
    return expires_at <= now


def _download_filename(item: WorkspaceFile) -> str:
    meta = item.meta or {}
    candidate = meta.get("originalFilename") or meta.get("original_filename") or item.name or item.storage_key
    fallback = item.name or f"download{f'.{item.extension}' if item.extension else ''}"
    filename = safe_original_filename(str(candidate), fallback=fallback, max_length=255)
    if item.extension and not filename.lower().endswith(f".{item.extension.lower()}"):
        filename = safe_original_filename(f"{filename}.{item.extension}", fallback=fallback, max_length=255)
    return filename


async def _get_file_by_token(db: AsyncSession, token: str) -> tuple[FileShare, WorkspaceFile]:
    result = await db.execute(
        select(FileShare, WorkspaceFile)
        .join(WorkspaceFile, WorkspaceFile.id == FileShare.file_id)
        .where(
            FileShare.token == token,
            FileShare.share_type == "link",
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    share, item = row
    if _is_expired(share.expires_at):
        raise HTTPException(status_code=410, detail="分享链接已过期")
    return share, item


async def _get_document_by_token(db: AsyncSession, token: str) -> tuple[DocumentShare, Document]:
    result = await db.execute(
        select(DocumentShare, Document)
        .join(Document, Document.id == DocumentShare.document_id)
        .where(
            DocumentShare.token == token,
            DocumentShare.share_type == "link",
            Document.deleted_at.is_(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    share, item = row
    if _is_expired(share.expires_at):
        raise HTTPException(status_code=410, detail="分享链接已过期")
    return share, item


@router.get("/files/{token}", response_model=dict)
async def get_shared_file(token: str, db: AsyncSession = Depends(get_session)):
    share, item = await _get_file_by_token(db, token)
    return {
        "success": True,
        "data": {
            "id": str(item.id),
            "name": item.name,
            "extension": item.extension,
            "mimeType": item.mime_type,
            "size": item.size,
            "permission": share.permission,
            "downloadUrl": f"/api/v1/share/files/{token}/download",
            "createdAt": _dt(item.created_at),
            "sharedAt": _dt(share.created_at),
            "expiresAt": _dt(share.expires_at),
        },
    }


@router.get("/files/{token}/download")
async def download_shared_file(token: str, db: AsyncSession = Depends(get_session)):
    _, item = await _get_file_by_token(db, token)
    storage = get_storage()
    filename = _download_filename(item)
    headers = {"Content-Disposition": download_content_disposition(filename)}
    local = storage.get_local_path(item.storage_key)
    if local:
        return FileResponse(str(local), media_type=item.mime_type, headers=headers)

    data = await storage.read(item.storage_key)
    return StreamingResponse(io.BytesIO(data), media_type=item.mime_type, headers=headers)


@router.get("/documents/{token}", response_model=dict)
async def get_shared_document(token: str, db: AsyncSession = Depends(get_session)):
    share, item = await _get_document_by_token(db, token)
    return {
        "success": True,
        "data": {
            "id": str(item.id),
            "title": item.title,
            "content": item.content or {},
            "contentText": item.content_text,
            "status": item.status,
            "permission": share.permission,
            "createdAt": _dt(item.created_at),
            "updatedAt": _dt(item.updated_at),
            "sharedAt": _dt(share.created_at),
            "expiresAt": _dt(share.expires_at),
        },
    }
