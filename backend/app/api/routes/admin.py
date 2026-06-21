from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.core.config import get_settings
from app.models.ai import AIModelConfig
from app.models.billing import Order, Payment, PaymentProviderConfig, Plan, Subscription
from app.models.drive import WorkspaceFile
from app.models.operations import AuditLog, Job, UsageRecord
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/admin", tags=["admin"])


def _dt(value):
    return value.isoformat() if value else None


async def _is_workspace_owner(db: AsyncSession, user: User, workspace: Workspace) -> bool:
    if workspace.owner_id == user.id:
        return True
    member = await db.scalar(
        select(WorkspaceMember.id).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active",
        )
    )
    return bool(member)


@router.get("/overview", response_model=dict)
async def admin_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await _is_workspace_owner(db, user, workspace)
    file_count = await db.scalar(select(func.count(WorkspaceFile.id)).where(WorkspaceFile.workspace_id == workspace.id))
    job_count = await db.scalar(select(func.count(Job.id)).where(Job.workspace_id == workspace.id))
    member_count = await db.scalar(select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace.id))
    usage_count = await db.scalar(select(func.count(UsageRecord.id)).where(UsageRecord.workspace_id == workspace.id))
    order_count = await db.scalar(select(func.count(Order.id)).where(Order.workspace_id == workspace.id))
    return {
        "success": True,
        "data": {
            "workspace": {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
                "plan": workspace.plan,
                "storageQuota": workspace.storage_quota,
                "aiQuota": workspace.ai_quota,
            },
            "metrics": {
                "files": int(file_count or 0),
                "jobs": int(job_count or 0),
                "members": int(member_count or 0),
                "usageRecords": int(usage_count or 0),
                "orders": int(order_count or 0),
            },
        },
    }


@router.get("/users", response_model=dict)
async def admin_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace.id)
        .order_by(WorkspaceMember.joined_at.desc())
    )
    return {
        "success": True,
        "data": [
            {
                "memberId": str(member.id),
                "userId": str(member.user_id) if member.user_id else None,
                "name": account.name,
                "email": account.email,
                "phone": account.phone,
                "status": member.status,
                "joinedAt": _dt(member.joined_at),
            }
            for member, account in result.all()
        ],
    }


@router.get("/workspaces", response_model=dict)
async def admin_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(Workspace)
        .where(Workspace.owner_id == user.id)
        .order_by(Workspace.created_at.desc())
        .limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "name": item.name,
                "slug": item.slug,
                "plan": item.plan,
                "storageQuota": item.storage_quota,
                "aiQuota": item.ai_quota,
                "createdAt": _dt(item.created_at),
            }
            for item in result.scalars().all()
        ],
    }


@router.get("/jobs", response_model=dict)
async def admin_jobs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(Job).where(Job.workspace_id == workspace.id).order_by(Job.created_at.desc()).limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "type": item.type,
                "status": item.status,
                "progress": item.progress,
                "errorMessage": item.error_message,
                "createdAt": _dt(item.created_at),
                "finishedAt": _dt(item.finished_at),
            }
            for item in result.scalars().all()
        ],
    }


@router.get("/files", response_model=dict)
async def admin_files(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(WorkspaceFile).where(WorkspaceFile.workspace_id == workspace.id).order_by(WorkspaceFile.created_at.desc()).limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "name": item.name,
                "extension": item.extension,
                "mimeType": item.mime_type,
                "size": item.size,
                "status": item.status,
                "parseStatus": item.parse_status,
                "aiStatus": item.ai_status,
                "createdAt": _dt(item.created_at),
            }
            for item in result.scalars().all()
        ],
    }


@router.get("/orders", response_model=dict)
async def admin_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(Order).where(Order.workspace_id == workspace.id).order_by(Order.created_at.desc()).limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "orderNo": item.order_no,
                "amount": float(item.amount or 0),
                "currency": item.currency,
                "status": item.status,
                "paymentProvider": item.payment_provider,
                "createdAt": _dt(item.created_at),
                "paidAt": _dt(item.paid_at),
            }
            for item in result.scalars().all()
        ],
    }


@router.get("/payments", response_model=dict)
async def admin_payments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(Payment, Order)
        .join(Order, Order.id == Payment.order_id)
        .where(Order.workspace_id == workspace.id)
        .order_by(Payment.created_at.desc())
        .limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(payment.id),
                "orderNo": order.order_no,
                "provider": payment.provider,
                "status": payment.status,
                "amount": float(payment.amount or 0),
                "currency": payment.currency,
                "createdAt": _dt(payment.created_at),
                "paidAt": _dt(payment.paid_at),
            }
            for payment, order in result.all()
        ],
    }


@router.get("/model-configs", response_model=dict)
async def admin_model_configs(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(AIModelConfig).order_by(AIModelConfig.priority.asc(), AIModelConfig.model_name.asc()))
    settings = get_settings()
    rows = [
        {
            "id": str(item.id),
            "provider": item.provider,
            "modelName": item.model_name,
            "displayName": item.display_name,
            "baseUrl": item.base_url,
            "capabilities": item.capabilities or {},
            "enabled": item.enabled,
            "priority": item.priority,
        }
        for item in result.scalars().all()
    ]
    if not rows:
        rows.append(
            {
                "id": "env-default",
                "provider": "openai-compatible",
                "modelName": settings.ai_gateway_model,
                "displayName": settings.ai_gateway_model,
                "baseUrl": settings.ai_gateway_base_url,
                "capabilities": {"chat": True, "summary": True, "file_ai": True},
                "enabled": bool(settings.ai_gateway_api_key),
                "priority": 100,
            }
        )
    return {"success": True, "data": rows}


@router.get("/storage", response_model=dict)
async def admin_storage(_: User = Depends(get_current_user)):
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "provider": settings.storage_backend,
            "localPath": settings.local_storage_path if settings.storage_backend == "local" else None,
            "ossEndpoint": settings.oss_endpoint or None,
            "ossBucket": settings.oss_bucket_name or None,
            "ossBaseUrl": settings.oss_base_url or None,
            "configured": settings.storage_backend == "local"
            or all([settings.oss_endpoint, settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_bucket_name]),
        },
    }


@router.get("/payment-configs", response_model=dict)
async def admin_payment_configs(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(PaymentProviderConfig).order_by(PaymentProviderConfig.sort_order.asc()))
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "code": item.code,
                "name": item.name,
                "providerType": item.provider_type,
                "currencies": item.supported_currencies or [],
                "regions": item.supported_regions or [],
                "active": item.active,
                "sandbox": item.sandbox,
            }
            for item in result.scalars().all()
        ],
    }


@router.get("/risk", response_model=dict)
async def admin_risk(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    failed_jobs = await db.scalar(select(func.count(Job.id)).where(Job.workspace_id == workspace.id, Job.status == "failed"))
    pending_orders = await db.scalar(select(func.count(Order.id)).where(Order.workspace_id == workspace.id, Order.status == "pending"))
    deleted_files = await db.scalar(select(func.count(WorkspaceFile.id)).where(WorkspaceFile.workspace_id == workspace.id, WorkspaceFile.status == "deleted"))
    return {
        "success": True,
        "data": {
            "failedJobs": int(failed_jobs or 0),
            "pendingOrders": int(pending_orders or 0),
            "deletedFiles": int(deleted_files or 0),
            "alerts": [
                "真实支付接入后需要开启 webhook 验签",
                "生产环境需要启用 Redis 限流和审计导出",
            ],
        },
    }


@router.get("/announcements", response_model=dict)
async def admin_announcements(_: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": [
            {"id": "launch", "title": "序光一期工作台上线", "status": "draft", "audience": "all"},
            {"id": "billing", "title": "商业化套餐支持本地模拟支付", "status": "draft", "audience": "admin"},
        ],
    }


@router.get("/system", response_model=dict)
async def admin_system(_: User = Depends(get_current_user)):
    settings = get_settings()
    return {
        "success": True,
        "data": {
            "appName": settings.app_name,
            "environment": settings.app_env,
            "debug": settings.debug,
            "apiPrefix": settings.api_prefix,
            "corsOrigins": settings.cors_origin_list,
            "redisUrl": settings.redis_url,
            "celeryBrokerUrl": settings.celery_broker_url,
            "paymentProvider": settings.payment_provider,
        },
    }


@router.get("/commerce", response_model=dict)
async def admin_commerce(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    plans = await db.execute(select(Plan).where(Plan.status == "active").order_by(Plan.sort_order.asc()))
    subscription = await db.scalar(
        select(Subscription).where(Subscription.workspace_id == workspace.id).order_by(Subscription.created_at.desc())
    )
    orders = await db.execute(
        select(Order).where(Order.workspace_id == workspace.id).order_by(Order.created_at.desc()).limit(20)
    )
    return {
        "success": True,
        "data": {
            "plans": [{"code": p.code, "name": p.name, "currency": p.currency} for p in plans.scalars().all()],
            "subscription": {
                "id": str(subscription.id),
                "status": subscription.status,
                "billingCycle": subscription.billing_cycle,
            }
            if subscription
            else None,
            "orders": [
                {
                    "id": str(item.id),
                    "orderNo": item.order_no,
                    "amount": float(item.amount),
                    "currency": item.currency,
                    "status": item.status,
                    "createdAt": _dt(item.created_at),
                }
                for item in orders.scalars().all()
            ],
        },
    }


@router.get("/audit-logs", response_model=dict)
async def admin_audit_logs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(AuditLog).where(AuditLog.workspace_id == workspace.id).order_by(AuditLog.created_at.desc()).limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "action": item.action,
                "resourceType": item.resource_type,
                "resourceId": str(item.resource_id) if item.resource_id else None,
                "metadata": item.meta or {},
                "createdAt": _dt(item.created_at),
            }
            for item in result.scalars().all()
        ],
    }

