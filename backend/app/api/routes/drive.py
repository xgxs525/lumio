from __future__ import annotations

import io
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.core.config import get_settings
from app.models.drive import FileShare, FileVersion, Folder, WorkspaceFile
from app.models.operations import AuditLog
from app.models.user import User
from app.services.billing import assert_storage_quota
from app.services.bootstrap import ensure_user_workspace
from app.services.storage import get_storage
from app.utils.files import ALLOWED_UPLOAD_EXTENSIONS, download_content_disposition, new_storage_key, safe_original_filename

router = APIRouter(prefix="/drive", tags=["drive"])

TEXT_PREVIEW_EXTENSIONS = {
    ".csv",
    ".json",
    ".log",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".py",
    ".sql",
}
TEXT_PREVIEW_MIME_PREFIXES = ("text/",)
TEXT_PREVIEW_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/x-yaml",
}
PREVIEW_LIMIT_BYTES = 256 * 1024


class DriveFileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=180)
    extension: str = Field(default=".txt", max_length=16)
    mime_type: str = Field(default="text/plain", max_length=120)
    content: str = ""
    folder_id: str | None = None


class ShareCreate(BaseModel):
    share_type: str = Field(default="link", pattern="^(link|workspace|team)$")
    permission: str = Field(default="view", pattern="^(view|comment|edit)$")


class SignedUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    size: int = Field(default=0, ge=0)
    mime_type: str = Field(default="application/octet-stream", max_length=160)
    folder_id: str | None = None


class CompleteUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    storage_key: str = Field(..., min_length=1)
    size: int = Field(default=0, ge=0)
    mime_type: str = Field(default="application/octet-stream", max_length=160)
    folder_id: str | None = None
    checksum: str | None = Field(default=None, max_length=128)


class VersionCreateRequest(BaseModel):
    storage_key: str = Field(..., min_length=1)
    size: int = Field(default=0, ge=0)
    checksum: str | None = Field(default=None, max_length=128)


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


def _file_payload(item: WorkspaceFile):
    meta = item.meta or {}
    original_filename = safe_original_filename(
        str(meta.get("originalFilename") or meta.get("original_filename") or item.name),
        fallback=item.name or "download",
    )
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "folderId": str(item.folder_id) if item.folder_id else None,
        "name": item.name,
        "originalFilename": original_filename,
        "storedFilename": Path(item.storage_key).name,
        "extension": item.extension,
        "mimeType": item.mime_type,
        "size": item.size,
        "storageProvider": item.storage_provider,
        "storageKey": item.storage_key,
        "status": item.status,
        "parseStatus": item.parse_status,
        "aiStatus": item.ai_status,
        "metadata": item.meta or {},
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


def _folder_payload(item: Folder):
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "parentId": str(item.parent_id) if item.parent_id else None,
        "name": item.name,
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


def _share_payload(item: FileShare):
    return {
        "id": str(item.id),
        "fileId": str(item.file_id),
        "workspaceId": str(item.workspace_id),
        "shareType": item.share_type,
        "permission": item.permission,
        "token": item.token,
        "shareUrl": f"/share/files/{item.token}" if item.token else None,
        "expiresAt": _dt(item.expires_at),
        "createdBy": str(item.created_by) if item.created_by else None,
        "createdAt": _dt(item.created_at),
    }


def _version_payload(item: FileVersion):
    return {
        "id": str(item.id),
        "fileId": str(item.file_id),
        "versionNo": item.version_no,
        "storageKey": item.storage_key,
        "size": item.size,
        "checksum": item.checksum,
        "createdBy": str(item.created_by) if item.created_by else None,
        "createdAt": _dt(item.created_at),
    }


def _download_filename(item: WorkspaceFile) -> str:
    meta = item.meta or {}
    candidate = meta.get("originalFilename") or meta.get("original_filename") or item.name or Path(item.storage_key).name
    fallback = item.name or f"download{f'.{item.extension}' if item.extension else ''}"
    filename = safe_original_filename(str(candidate), fallback=fallback, max_length=255)
    if item.extension and not Path(filename).suffix:
        filename = safe_original_filename(f"{filename}.{item.extension}", fallback=fallback, max_length=255)
    return filename


async def _get_workspace_file(db: AsyncSession, workspace_id: uuid.UUID, file_id: str) -> WorkspaceFile:
    file_uuid = _uuid_or_400(file_id)
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


async def _validate_folder(db: AsyncSession, workspace_id: uuid.UUID, folder_id: str | None) -> uuid.UUID | None:
    folder_uuid = _uuid_or_400(folder_id, "folder_id") if folder_id else None
    if not folder_uuid:
        return None
    folder_result = await db.execute(
        select(Folder).where(
            Folder.id == folder_uuid,
            Folder.workspace_id == workspace_id,
            Folder.deleted_at.is_(None),
        )
    )
    if folder_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return folder_uuid


async def _get_file_share(db: AsyncSession, workspace_id: uuid.UUID, share_id: str) -> FileShare:
    share_uuid = _uuid_or_400(share_id, "share_id")
    result = await db.execute(
        select(FileShare)
        .join(WorkspaceFile, WorkspaceFile.id == FileShare.file_id)
        .where(
            FileShare.id == share_uuid,
            FileShare.workspace_id == workspace_id,
            WorkspaceFile.workspace_id == workspace_id,
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="分享记录不存在")
    return item


@router.get("/overview", response_model=dict)
async def drive_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    file_stats = await db.execute(
        select(func.count(WorkspaceFile.id), func.coalesce(func.sum(WorkspaceFile.size), 0)).where(
            WorkspaceFile.workspace_id == workspace.id,
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    file_count, storage_used = file_stats.one()
    folder_count = await db.scalar(
        select(func.count(Folder.id)).where(Folder.workspace_id == workspace.id, Folder.deleted_at.is_(None))
    )
    return {
        "success": True,
        "data": {
            "workspaceId": str(workspace.id),
            "fileCount": file_count or 0,
            "folderCount": folder_count or 0,
            "storageUsed": int(storage_used or 0),
            "storageQuota": workspace.storage_quota,
        },
    }


@router.get("/folders", response_model=dict)
async def list_folders(
    parent_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = select(Folder).where(Folder.workspace_id == workspace.id, Folder.deleted_at.is_(None))
    if parent_id:
        stmt = stmt.where(Folder.parent_id == _uuid_or_400(parent_id, "parent_id"))
    else:
        stmt = stmt.where(Folder.parent_id.is_(None))
    result = await db.execute(stmt.order_by(Folder.created_at.asc()))
    return {"success": True, "data": [_folder_payload(item) for item in result.scalars().all()]}


@router.post("/folders", response_model=dict)
async def create_folder(
    name: str = Form(...),
    parent_id: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")

    parent_uuid = _uuid_or_400(parent_id, "parent_id") if parent_id else None
    if parent_uuid:
        parent_result = await db.execute(
            select(Folder).where(
                Folder.id == parent_uuid,
                Folder.workspace_id == workspace.id,
                Folder.deleted_at.is_(None),
            )
        )
        if parent_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="父级文件夹不存在")

    result = await db.execute(
        select(Folder).where(
            Folder.workspace_id == workspace.id,
            Folder.parent_id == parent_uuid if parent_uuid else Folder.parent_id.is_(None),
            Folder.name == clean_name,
            Folder.deleted_at.is_(None),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"success": True, "data": _folder_payload(existing)}

    folder = Folder(workspace_id=workspace.id, owner_id=user.id, parent_id=parent_uuid, name=clean_name)
    db.add(folder)
    await db.flush()
    return {"success": True, "data": _folder_payload(folder)}


@router.get("/files", response_model=dict)
async def list_files(
    folder_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = select(WorkspaceFile).where(
        WorkspaceFile.workspace_id == workspace.id,
        WorkspaceFile.deleted_at.is_(None),
    )
    if folder_id:
        stmt = stmt.where(WorkspaceFile.folder_id == _uuid_or_400(folder_id, "folder_id"))
    else:
        stmt = stmt.where(WorkspaceFile.folder_id.is_(None))
    result = await db.execute(stmt.order_by(WorkspaceFile.created_at.desc()))
    return {"success": True, "data": [_file_payload(item) for item in result.scalars().all()]}


@router.post("/files/create-upload-url", response_model=dict)
async def create_file_upload_url(
    payload: SignedUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    filename = safe_original_filename(payload.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    await _validate_folder(db, workspace.id, payload.folder_id)
    await assert_storage_quota(db, workspace, payload.size)

    storage_key, _ = new_storage_key(filename, prefix=f"workspaces/{workspace.id}/drive")
    storage = get_storage()
    expires_in = 900
    if hasattr(storage, "presigned_upload_url") and get_settings().storage_backend == "oss":
        upload_url = storage.presigned_upload_url(storage_key, expires=expires_in)  # type: ignore[attr-defined]
        direct_upload = True
        method = "PUT"
    else:
        upload_url = "/api/v1/drive/files/upload"
        direct_upload = False
        method = "POST"

    return {
        "success": True,
        "data": {
            "directUpload": direct_upload,
            "uploadUrl": upload_url,
            "completeUrl": "/api/v1/drive/files/complete-upload",
            "method": method,
            "headers": {"Content-Type": payload.mime_type} if direct_upload else {},
            "storageKey": storage_key,
            "originalFilename": filename,
            "expiresIn": expires_in,
        },
    }


@router.post("/files/complete-upload", response_model=dict)
async def complete_file_upload(
    payload: CompleteUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    filename = safe_original_filename(payload.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    folder_uuid = await _validate_folder(db, workspace.id, payload.folder_id)
    await assert_storage_quota(db, workspace, payload.size)

    record = WorkspaceFile(
        workspace_id=workspace.id,
        owner_id=user.id,
        folder_id=folder_uuid,
        name=filename,
        extension=ext.lstrip("."),
        mime_type=payload.mime_type or "application/octet-stream",
        size=payload.size,
        storage_provider=get_settings().storage_backend,
        storage_key=payload.storage_key,
        checksum=payload.checksum,
        parse_status="pending",
        ai_status="not_ready",
        meta={
            "source": "direct_upload",
            "originalFilename": filename,
            "storedFilename": Path(payload.storage_key).name,
        },
    )
    db.add(record)
    await db.flush()
    return {"success": True, "data": _file_payload(record)}


@router.get("/files/{file_id}", response_model=dict)
async def get_drive_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    return {"success": True, "data": _file_payload(item)}


@router.post("/files", response_model=dict)
async def create_drive_file(
    payload: DriveFileCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    base_name = safe_original_filename(payload.name.strip())
    if not base_name:
        raise HTTPException(status_code=400, detail="文件名称不能为空")

    ext = payload.extension.strip().lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    if not base_name.lower().endswith(ext):
        filename = f"{base_name}{ext}"
    else:
        filename = base_name

    folder_uuid = _uuid_or_400(payload.folder_id, "folder_id") if payload.folder_id else None
    if folder_uuid:
        folder_result = await db.execute(
            select(Folder).where(
                Folder.id == folder_uuid,
                Folder.workspace_id == workspace.id,
                Folder.deleted_at.is_(None),
            )
        )
        if folder_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="文件夹不存在")

    data = payload.content.encode("utf-8")
    await assert_storage_quota(db, workspace, len(data))
    storage_key, _ = new_storage_key(filename, prefix=f"workspaces/{workspace.id}/drive")
    storage = get_storage()
    await storage.save(storage_key, data)

    record = WorkspaceFile(
        workspace_id=workspace.id,
        owner_id=user.id,
        folder_id=folder_uuid,
        name=filename,
        extension=ext.lstrip("."),
        mime_type=payload.mime_type or "text/plain",
        size=len(data),
        storage_provider="local",
        storage_key=storage_key,
        parse_status="pending",
        ai_status="not_ready",
        meta={
            "source": "drive_create",
            "originalFilename": filename,
            "storedFilename": Path(storage_key).name,
        },
    )
    db.add(record)
    await db.flush()
    return {"success": True, "data": _file_payload(record)}


@router.post("/files/upload", response_model=dict)
async def upload_drive_file(
    file: UploadFile | None = File(default=None),
    folder_id: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="没有选择文件")

    workspace = await ensure_user_workspace(db, user)
    filename = safe_original_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    folder_uuid = _uuid_or_400(folder_id, "folder_id") if folder_id else None
    if folder_uuid:
        folder_result = await db.execute(
            select(Folder).where(
                Folder.id == folder_uuid,
                Folder.workspace_id == workspace.id,
                Folder.deleted_at.is_(None),
            )
        )
        if folder_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="文件夹不存在")

    data = await file.read()
    await assert_storage_quota(db, workspace, len(data))
    storage_key, _ = new_storage_key(filename, prefix=f"workspaces/{workspace.id}/drive")
    storage = get_storage()
    await storage.save(storage_key, data)

    record = WorkspaceFile(
        workspace_id=workspace.id,
        owner_id=user.id,
        folder_id=folder_uuid,
        name=filename,
        extension=ext.lstrip("."),
        mime_type=file.content_type or "application/octet-stream",
        size=len(data),
        storage_provider="local",
        storage_key=storage_key,
        parse_status="pending",
        ai_status="not_ready",
        meta={
            "source": "drive_upload",
            "originalFilename": filename,
            "storedFilename": Path(storage_key).name,
        },
    )
    db.add(record)
    await db.flush()
    return {"success": True, "data": _file_payload(record)}


@router.get("/files/{file_id}/download")
async def download_drive_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)

    storage = get_storage()
    filename = _download_filename(item)
    headers = {"Content-Disposition": download_content_disposition(filename)}
    local = storage.get_local_path(item.storage_key)
    if local:
        return FileResponse(str(local), media_type=item.mime_type, headers=headers)

    data = await storage.read(item.storage_key)
    return StreamingResponse(io.BytesIO(data), media_type=item.mime_type, headers=headers)


@router.get("/files/{file_id}/preview", response_model=dict)
async def preview_drive_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    ext = f".{item.extension.lower()}" if item.extension else Path(item.name).suffix.lower()
    mime_type = item.mime_type or "application/octet-stream"
    is_text = (
        ext in TEXT_PREVIEW_EXTENSIONS
        or mime_type in TEXT_PREVIEW_MIME_TYPES
        or any(mime_type.startswith(prefix) for prefix in TEXT_PREVIEW_MIME_PREFIXES)
    )
    download_url = f"/api/v1/drive/files/{item.id}/download"

    if is_text:
        data = await get_storage().read(item.storage_key)
        clipped = data[:PREVIEW_LIMIT_BYTES]
        content = clipped.decode("utf-8", errors="replace")
        return {
            "success": True,
            "data": {
                "kind": "text",
                "file": _file_payload(item),
                "content": content,
                "truncated": len(data) > PREVIEW_LIMIT_BYTES,
                "downloadUrl": download_url,
            },
        }

    kind = "image" if mime_type.startswith("image/") else "pdf" if mime_type == "application/pdf" else "download"
    return {
        "success": True,
        "data": {
            "kind": kind,
            "file": _file_payload(item),
            "content": "",
            "truncated": False,
            "downloadUrl": download_url,
        },
    }


@router.get("/files/{file_id}/signed-preview-url", response_model=dict)
async def signed_preview_url(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    storage = get_storage()
    expires_in = 900
    signed = None
    if hasattr(storage, "presigned_download_url") and get_settings().storage_backend == "oss":
        signed = storage.presigned_download_url(item.storage_key, expires=expires_in)  # type: ignore[attr-defined]
    public_url = signed or storage.public_url(item.storage_key)
    download_url = public_url or f"/api/v1/drive/files/{item.id}/download"
    return {
        "success": True,
        "data": {
            "file": _file_payload(item),
            "previewUrl": download_url,
            "downloadUrl": download_url,
            "external": bool(public_url),
            "expiresIn": expires_in if public_url else None,
        },
    }


@router.get("/files/{file_id}/versions", response_model=dict)
async def list_file_versions(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    result = await db.execute(
        select(FileVersion).where(FileVersion.file_id == item.id).order_by(FileVersion.version_no.desc())
    )
    return {"success": True, "data": [_version_payload(version) for version in result.scalars().all()]}


@router.post("/files/{file_id}/versions", response_model=dict)
async def create_file_version(
    file_id: str,
    payload: VersionCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    latest_no = await db.scalar(select(func.max(FileVersion.version_no)).where(FileVersion.file_id == item.id))
    version = FileVersion(
        file_id=item.id,
        version_no=int(latest_no or 0) + 1,
        storage_key=payload.storage_key,
        size=payload.size,
        checksum=payload.checksum,
        created_by=user.id,
    )
    item.storage_key = payload.storage_key
    item.size = payload.size
    item.checksum = payload.checksum
    db.add(version)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="file.version.create",
            resource_type="file",
            resource_id=item.id,
            meta={"versionNo": version.version_no},
        )
    )
    await db.flush()
    return {"success": True, "data": _version_payload(version)}


@router.get("/files/{file_id}/shares", response_model=dict)
async def list_file_shares(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    result = await db.execute(
        select(FileShare).where(FileShare.file_id == item.id, FileShare.workspace_id == workspace.id).order_by(FileShare.created_at.desc())
    )
    return {"success": True, "data": [_share_payload(share) for share in result.scalars().all()]}


@router.post("/files/{file_id}/shares", response_model=dict)
async def create_file_share(
    file_id: str,
    payload: ShareCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)
    share = FileShare(
        file_id=item.id,
        workspace_id=workspace.id,
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
            action="file.share.create",
            resource_type="file",
            resource_id=item.id,
            meta={"shareType": payload.share_type, "permission": payload.permission},
        )
    )
    await db.flush()
    return {"success": True, "data": _share_payload(share)}


@router.delete("/files/shares/{share_id}", response_model=dict)
async def delete_file_share(
    share_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    share = await _get_file_share(db, workspace.id, share_id)
    file_id = share.file_id
    await db.delete(share)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="file.share.delete",
            resource_type="file",
            resource_id=file_id,
            meta={"shareId": share_id},
        )
    )
    return {"success": True}


@router.delete("/files/{file_id}", response_model=dict)
async def delete_drive_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)

    item.status = "deleted"
    item.deleted_at = datetime.now(UTC)
    return {"success": True}


# ── 回收站 ──────────────────────────────────────

@router.get("/trash", response_model=dict)
async def list_trash(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = (
        select(WorkspaceFile)
        .where(
            WorkspaceFile.workspace_id == workspace.id,
            WorkspaceFile.deleted_at.isnot(None),
        )
        .order_by(WorkspaceFile.deleted_at.desc())
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return {"data": [_file_payload(item) for item in items], "total": len(items)}


@router.post("/files/{file_id}/restore", response_model=dict)
async def restore_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = select(WorkspaceFile).where(
        WorkspaceFile.id == file_id,
        WorkspaceFile.workspace_id == workspace.id,
        WorkspaceFile.deleted_at.isnot(None),
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="File not found in trash")

    item.status = "active"
    item.deleted_at = None
    db.add(AuditLog(workspace_id=workspace.id, user_id=user.id, action="file.restore", resource_type="file", resource_id=file_id))
    return {"success": True}


@router.delete("/files/{file_id}/permanent", response_model=dict)
async def permanent_delete_file(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_workspace_file(db, workspace.id, file_id)

    # Remove from storage
    storage = get_storage()
    try:
        if item.storage_key:
            storage.delete(item.storage_key)
    except Exception:
        pass

    # Delete related shares and versions
    await db.execute(select(FileShare).where(FileShare.file_id == file_id))
    await db.execute(select(FileVersion).where(FileVersion.file_id == file_id))

    await db.delete(item)
    db.add(AuditLog(workspace_id=workspace.id, user_id=user.id, action="file.permanent_delete", resource_type="file", resource_id=file_id))
    return {"success": True}


@router.post("/trash/empty", response_model=dict)
async def empty_trash(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = select(WorkspaceFile).where(
        WorkspaceFile.workspace_id == workspace.id,
        WorkspaceFile.deleted_at.isnot(None),
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    storage = get_storage()
    count = 0
    for item in items:
        try:
            if item.storage_key:
                storage.delete(item.storage_key)
        except Exception:
            pass
        await db.delete(item)
        count += 1

    db.add(AuditLog(workspace_id=workspace.id, user_id=user.id, action="trash.empty", resource_type="trash", resource_id=workspace.id, meta={"count": count}))
    return {"success": True, "deleted_count": count}
