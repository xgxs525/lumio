from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.operations import Job
from app.models.user import User
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=80)
    input: dict = Field(default_factory=dict)


class JobUpdate(BaseModel):
    status: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    output: dict | None = None
    error_message: str | None = None


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


def _job_payload(item: Job):
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id) if item.workspace_id else None,
        "userId": str(item.user_id) if item.user_id else None,
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


@router.get("", response_model=dict)
async def list_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(Job).where(Job.workspace_id == workspace.id).order_by(Job.created_at.desc()).limit(100)
    )
    return {"success": True, "data": [_job_payload(item) for item in result.scalars().all()]}


@router.get("/{job_id}", response_model=dict)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    job_uuid = _uuid_or_400(job_id)
    result = await db.execute(select(Job).where(Job.id == job_uuid, Job.workspace_id == workspace.id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "data": _job_payload(item)}


@router.post("", response_model=dict)
async def create_job(
    payload: JobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = Job(
        workspace_id=workspace.id,
        user_id=user.id,
        type=payload.type,
        status="pending",
        progress=0,
        input=payload.input,
        output={},
    )
    db.add(item)
    await db.flush()
    return {"success": True, "data": _job_payload(item)}


@router.patch("/{job_id}", response_model=dict)
async def update_job(
    job_id: str,
    payload: JobUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    job_uuid = _uuid_or_400(job_id)
    result = await db.execute(select(Job).where(Job.id == job_uuid, Job.workspace_id == workspace.id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if payload.status is not None:
        item.status = payload.status
        if payload.status == "running" and item.started_at is None:
            item.started_at = datetime.now(UTC)
        if payload.status in {"success", "failed", "cancelled"}:
            item.finished_at = datetime.now(UTC)
    if payload.progress is not None:
        item.progress = payload.progress
    if payload.output is not None:
        item.output = payload.output
    if payload.error_message is not None:
        item.error_message = payload.error_message
    await db.flush()
    return {"success": True, "data": _job_payload(item)}
