from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.drive import Folder, WorkspaceFile
from app.models.operations import AuditLog
from app.models.user import User
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: str | None = None


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


def _folder_payload(item: Folder, file_count: int = 0, child_count: int = 0) -> dict:
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id),
        "parentId": str(item.parent_id) if item.parent_id else None,
        "name": item.name,
        "fileCount": file_count,
        "childCount": child_count,
        "createdAt": _dt(item.created_at),
        "updatedAt": _dt(item.updated_at),
    }


async def _get_folder(db: AsyncSession, workspace_id: uuid.UUID, folder_id: str) -> Folder:
    folder_uuid = _uuid_or_400(folder_id, "folder_id")
    result = await db.execute(
        select(Folder).where(
            Folder.id == folder_uuid,
            Folder.workspace_id == workspace_id,
            Folder.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    return item


@router.get("/{folder_id}", response_model=dict)
async def get_folder_detail(
    folder_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_folder(db, workspace.id, folder_id)
    file_count = len(
        (
            await db.execute(
                select(WorkspaceFile.id).where(
                    WorkspaceFile.workspace_id == workspace.id,
                    WorkspaceFile.folder_id == item.id,
                    WorkspaceFile.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    child_count = len(
        (
            await db.execute(
                select(Folder.id).where(
                    Folder.workspace_id == workspace.id,
                    Folder.parent_id == item.id,
                    Folder.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    return {"success": True, "data": _folder_payload(item, file_count=file_count, child_count=child_count)}


@router.patch("/{folder_id}", response_model=dict)
async def update_folder(
    folder_id: str,
    payload: FolderUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_folder(db, workspace.id, folder_id)
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.parent_id is not None:
        parent_uuid = _uuid_or_400(payload.parent_id, "parent_id") if payload.parent_id else None
        if parent_uuid == item.id:
            raise HTTPException(status_code=400, detail="文件夹不能移动到自身下面")
        item.parent_id = parent_uuid
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="folder.update",
            resource_type="folder",
            resource_id=item.id,
            meta={"name": item.name},
        )
    )
    await db.flush()
    return {"success": True, "data": _folder_payload(item)}


@router.delete("/{folder_id}", response_model=dict)
async def delete_folder(
    folder_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_folder(db, workspace.id, folder_id)
    item.deleted_at = datetime.now(UTC)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="folder.delete",
            resource_type="folder",
            resource_id=item.id,
            meta={"name": item.name},
        )
    )
    return {"success": True}
