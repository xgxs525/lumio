from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.drive import WorkspaceFile
from app.models.operations import UsageRecord
from app.models.user import User
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/usage", tags=["usage"])


def _dt(value):
    return value.isoformat() if value else None


def _record_payload(item: UsageRecord) -> dict:
    return {
        "id": str(item.id),
        "workspaceId": str(item.workspace_id) if item.workspace_id else None,
        "userId": str(item.user_id) if item.user_id else None,
        "usageType": item.usage_type,
        "quantity": float(item.quantity or Decimal("0")),
        "unit": item.unit,
        "modelName": item.model_name,
        "cost": float(item.cost or Decimal("0")),
        "metadata": item.meta or {},
        "createdAt": _dt(item.created_at),
    }


@router.get("/summary", response_model=dict)
async def usage_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    storage_used = await db.scalar(
        select(func.coalesce(func.sum(WorkspaceFile.size), 0)).where(
            WorkspaceFile.workspace_id == workspace.id,
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    ai_tokens = await db.scalar(
        select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
            UsageRecord.workspace_id == workspace.id,
            UsageRecord.usage_type.in_(["ai_tokens", "embedding_tokens"]),
        )
    )
    file_count = await db.scalar(
        select(func.count(WorkspaceFile.id)).where(
            WorkspaceFile.workspace_id == workspace.id,
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    return {
        "success": True,
        "data": {
            "workspaceId": str(workspace.id),
            "plan": workspace.plan,
            "storageUsed": int(storage_used or 0),
            "storageQuota": workspace.storage_quota,
            "storagePercent": round((int(storage_used or 0) / max(workspace.storage_quota, 1)) * 100, 2),
            "aiTokensUsed": float(ai_tokens or 0),
            "aiQuota": workspace.ai_quota,
            "aiPercent": round((float(ai_tokens or 0) / max(workspace.ai_quota, 1)) * 100, 2),
            "fileCount": int(file_count or 0),
        },
    }


@router.get("/records", response_model=dict)
async def list_usage_records(
    usage_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    stmt = (
        select(UsageRecord)
        .where(UsageRecord.workspace_id == workspace.id)
        .order_by(UsageRecord.created_at.desc())
        .limit(limit)
    )
    if usage_type:
        stmt = stmt.where(UsageRecord.usage_type == usage_type)
    result = await db.execute(stmt)
    return {"success": True, "data": [_record_payload(item) for item in result.scalars().all()]}
