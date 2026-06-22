from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.drive import FileTag, Tag, WorkspaceFile
from app.models.user import User
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str
    color: str = "blue"


class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    created_at: str | None = None


def _tag_payload(tag: Tag) -> dict:
    return {
        "id": str(tag.id),
        "name": tag.name,
        "color": tag.color,
        "created_at": tag.created_at.isoformat() if tag.created_at else None,
    }


async def _get_tag(db: AsyncSession, workspace_id: uuid.UUID, tag_id: str) -> Tag:
    stmt = select(Tag).where(Tag.id == tag_id, Tag.workspace_id == workspace_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


# ── 标签 CRUD ──────────────────────────────────

@router.get("", response_model=dict)
async def list_tags(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = select(Tag).where(Tag.workspace_id == workspace.id).order_by(Tag.name)
    result = await db.execute(stmt)
    tags = result.scalars().all()
    return {"data": [_tag_payload(t) for t in tags]}


@router.post("", response_model=dict)
async def create_tag(
    body: TagCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    tag = Tag(workspace_id=workspace.id, name=body.name, color=body.color)
    db.add(tag)
    await db.flush()
    return {"data": _tag_payload(tag)}


@router.delete("/{tag_id}", response_model=dict)
async def delete_tag(
    tag_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    tag = await _get_tag(db, workspace.id, tag_id)
    await db.delete(tag)
    return {"success": True}


# ── 文件标签关联 ──────────────────────────────

@router.get("/files/{file_id}", response_model=dict)
async def list_file_tags(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = (
        select(Tag)
        .join(FileTag, FileTag.tag_id == Tag.id)
        .where(FileTag.file_id == file_id, Tag.workspace_id == workspace.id)
        .order_by(Tag.name)
    )
    result = await db.execute(stmt)
    tags = result.scalars().all()
    return {"data": [_tag_payload(t) for t in tags]}


@router.post("/files/{file_id}", response_model=dict)
async def add_file_tags(
    file_id: str,
    tag_ids: list[str],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)

    # Verify file belongs to workspace
    file_stmt = select(WorkspaceFile).where(WorkspaceFile.id == file_id, WorkspaceFile.workspace_id == workspace.id)
    file_result = await db.execute(file_stmt)
    if not file_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="File not found")

    # Remove existing tags for this file
    del_stmt = select(FileTag).where(FileTag.file_id == file_id)
    del_result = await db.execute(del_stmt)
    for ft in del_result.scalars().all():
        await db.delete(ft)

    # Add new tags
    for tid in tag_ids:
        tag = await _get_tag(db, workspace.id, tid)
        db.add(FileTag(file_id=file_id, tag_id=tag.id))

    # Return updated tags
    tag_stmt = select(Tag).where(Tag.id.in_([uuid.UUID(t) for t in tag_ids])).order_by(Tag.name)
    tag_result = await db.execute(tag_stmt)
    return {"data": [_tag_payload(t) for t in tag_result.scalars().all()]}


@router.delete("/files/{file_id}/{tag_id}", response_model=dict)
async def remove_file_tag(
    file_id: str,
    tag_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    ft_stmt = select(FileTag).where(FileTag.file_id == file_id, FileTag.tag_id == tag_id)
    result = await db.execute(ft_stmt)
    ft = result.scalar_one_or_none()
    if not ft:
        raise HTTPException(status_code=404, detail="Tag not found on file")
    await db.delete(ft)
    return {"success": True}
