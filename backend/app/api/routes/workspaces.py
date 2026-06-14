from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.document import Document
from app.models.drive import Folder, WorkspaceFile
from app.models.knowledge import KnowledgeBase
from app.models.operations import Job
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    locale: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=64)
    logo_url: str | None = None


def _dt(value):
    return value.isoformat() if value else None


def _user_payload(user: User):
    return {
        "id": str(user.id),
        "email": user.email,
        "phone": user.phone,
        "name": user.name or user.nickname,
        "avatarUrl": user.avatar_url,
        "locale": user.locale,
        "timezone": user.timezone,
        "status": user.status,
    }


def _workspace_payload(workspace):
    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "slug": workspace.slug,
        "logoUrl": workspace.logo_url,
        "plan": workspace.plan,
        "storageQuota": workspace.storage_quota,
        "aiQuota": workspace.ai_quota,
        "locale": workspace.locale,
        "timezone": workspace.timezone,
        "createdAt": _dt(workspace.created_at),
        "updatedAt": _dt(workspace.updated_at),
    }


@router.get("/current", response_model=dict)
async def get_current_workspace(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    return {
        "success": True,
        "data": {
            "user": _user_payload(user),
            "workspace": _workspace_payload(workspace),
        },
    }


@router.patch("/current", response_model=dict)
async def update_current_workspace(
    payload: WorkspaceUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    if payload.name is not None:
        workspace.name = payload.name.strip()
    if payload.locale is not None:
        workspace.locale = payload.locale.strip()
    if payload.timezone is not None:
        workspace.timezone = payload.timezone.strip()
    if payload.logo_url is not None:
        workspace.logo_url = payload.logo_url.strip() or None
    await db.flush()
    return {
        "success": True,
        "data": {
            "user": _user_payload(user),
            "workspace": _workspace_payload(workspace),
        },
    }


@router.get("/overview", response_model=dict)
async def get_workspace_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)

    file_stats = await db.execute(
        select(
            func.count(WorkspaceFile.id),
            func.coalesce(func.sum(WorkspaceFile.size), 0),
        ).where(WorkspaceFile.workspace_id == workspace.id, WorkspaceFile.deleted_at.is_(None))
    )
    file_count, storage_used = file_stats.one()

    folder_count = await db.scalar(
        select(func.count(Folder.id)).where(Folder.workspace_id == workspace.id, Folder.deleted_at.is_(None))
    )
    document_count = await db.scalar(
        select(func.count(Document.id)).where(Document.workspace_id == workspace.id, Document.deleted_at.is_(None))
    )
    knowledge_count = await db.scalar(
        select(func.count(KnowledgeBase.id)).where(KnowledgeBase.workspace_id == workspace.id)
    )
    job_count = await db.scalar(select(func.count(Job.id)).where(Job.workspace_id == workspace.id))
    member_count = await db.scalar(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace.id)
    )

    recent_files = await db.execute(
        select(WorkspaceFile)
        .where(WorkspaceFile.workspace_id == workspace.id, WorkspaceFile.deleted_at.is_(None))
        .order_by(WorkspaceFile.created_at.desc())
        .limit(8)
    )
    recent_jobs = await db.execute(
        select(Job).where(Job.workspace_id == workspace.id).order_by(Job.created_at.desc()).limit(8)
    )

    return {
        "success": True,
        "data": {
            "workspace": _workspace_payload(workspace),
            "metrics": {
                "files": file_count or 0,
                "folders": folder_count or 0,
                "documents": document_count or 0,
                "knowledgeBases": knowledge_count or 0,
                "jobs": job_count or 0,
                "members": member_count or 0,
                "storageUsed": int(storage_used or 0),
                "storageQuota": workspace.storage_quota,
            },
            "recentFiles": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "extension": item.extension,
                    "size": item.size,
                    "status": item.status,
                    "createdAt": _dt(item.created_at),
                }
                for item in recent_files.scalars().all()
            ],
            "recentJobs": [
                {
                    "id": str(item.id),
                    "type": item.type,
                    "status": item.status,
                    "progress": item.progress,
                    "createdAt": _dt(item.created_at),
                }
                for item in recent_jobs.scalars().all()
            ],
        },
    }
