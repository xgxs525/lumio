from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Order, Payment, PaymentProviderConfig, Plan, Subscription
from app.models.drive import WorkspaceFile
from app.models.operations import AuditLog, UsageRecord
from app.models.workspace import Workspace, WorkspaceMember

GB = 1024 * 1024 * 1024


@dataclass(frozen=True)
class PlanSeed:
    code: str
    name: str
    description: str
    monthly: Decimal
    yearly: Decimal
    storage_quota: int
    ai_quota: int
    ai_request_quota: int
    member_limit: int
    advanced_model_enabled: bool
    enterprise_support_enabled: bool
    sort_order: int
    features: dict
    model_policy: dict


PLAN_SEEDS = [
    PlanSeed(
        code="free",
        name="免费版",
        description="适合个人体验、轻量文件处理和基础 AI 问答。",
        monthly=Decimal("0"),
        yearly=Decimal("0"),
        storage_quota=10 * GB,
        ai_quota=100_000,
        ai_request_quota=50,
        member_limit=1,
        advanced_model_enabled=False,
        enterprise_support_enabled=False,
        sort_order=10,
        features={
            "drive": True,
            "docs": True,
            "knowledge": True,
            "file_ai": True,
            "team": False,
            "automation": False,
            "audit": False,
        },
        model_policy={"allowedModels": ["standard"], "advancedModels": []},
    ),
    PlanSeed(
        code="pro",
        name="专业版",
        description="适合高频个人办公、自由职业者和单人业务工作台。",
        monthly=Decimal("49"),
        yearly=Decimal("499"),
        storage_quota=100 * GB,
        ai_quota=1_000_000,
        ai_request_quota=1_000,
        member_limit=3,
        advanced_model_enabled=False,
        enterprise_support_enabled=False,
        sort_order=20,
        features={
            "drive": True,
            "docs": True,
            "knowledge": True,
            "file_ai": True,
            "team": True,
            "automation": False,
            "audit": False,
        },
        model_policy={"allowedModels": ["standard", "fast"], "advancedModels": []},
    ),
    PlanSeed(
        code="team",
        name="团队版",
        description="适合小团队共享空间、知识库、任务协作和权限管理。",
        monthly=Decimal("199"),
        yearly=Decimal("1990"),
        storage_quota=1024 * GB,
        ai_quota=5_000_000,
        ai_request_quota=5_000,
        member_limit=20,
        advanced_model_enabled=True,
        enterprise_support_enabled=False,
        sort_order=30,
        features={
            "drive": True,
            "docs": True,
            "knowledge": True,
            "file_ai": True,
            "team": True,
            "automation": True,
            "audit": True,
        },
        model_policy={"allowedModels": ["standard", "fast", "advanced"], "advancedModels": ["advanced"]},
    ),
    PlanSeed(
        code="enterprise",
        name="企业版",
        description="适合大型组织、私有化部署、API 集成、企业安全和专属服务。",
        monthly=Decimal("0"),
        yearly=Decimal("0"),
        storage_quota=0,
        ai_quota=0,
        ai_request_quota=0,
        member_limit=0,
        advanced_model_enabled=True,
        enterprise_support_enabled=True,
        sort_order=40,
        features={
            "drive": True,
            "docs": True,
            "knowledge": True,
            "file_ai": True,
            "team": True,
            "automation": True,
            "audit": True,
            "privateDeploy": True,
            "apiAccess": True,
        },
        model_policy={"allowedModels": ["standard", "fast", "advanced", "enterprise"], "advancedModels": ["advanced", "enterprise"]},
    ),
]

PROVIDER_SEEDS = [
    {
        "code": "mock_cn",
        "name": "序光模拟支付",
        "provider_type": "mock",
        "supported_currencies": ["CNY"],
        "supported_regions": ["CN"],
        "sort_order": 10,
        "meta": {"settlement": "sandbox", "label": "本地开发支付"},
    },
    {
        "code": "alipay",
        "name": "支付宝",
        "provider_type": "wallet",
        "supported_currencies": ["CNY"],
        "supported_regions": ["CN"],
        "sort_order": 20,
        "meta": {"settlement": "domestic"},
    },
    {
        "code": "wechat_pay",
        "name": "微信支付",
        "provider_type": "wallet",
        "supported_currencies": ["CNY"],
        "supported_regions": ["CN"],
        "sort_order": 30,
        "meta": {"settlement": "domestic"},
    },
    {
        "code": "stripe",
        "name": "Stripe",
        "provider_type": "card",
        "supported_currencies": ["USD", "EUR", "HKD", "JPY"],
        "supported_regions": ["US", "EU", "HK", "JP", "SG"],
        "sort_order": 40,
        "meta": {"settlement": "international"},
    },
    {
        "code": "paypal",
        "name": "PayPal",
        "provider_type": "wallet",
        "supported_currencies": ["USD", "EUR", "HKD"],
        "supported_regions": ["US", "EU", "HK", "SG"],
        "sort_order": 50,
        "meta": {"settlement": "international"},
    },
]

CURRENCY_RATES = {
    "CNY": Decimal("1"),
    "USD": Decimal("0.14"),
    "EUR": Decimal("0.13"),
    "HKD": Decimal("1.08"),
    "JPY": Decimal("21.5"),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _decimal_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _convert_amount(amount: Decimal, currency: str) -> Decimal:
    code = currency.upper()
    if code == "CNY":
        return _decimal_money(amount)
    rate = CURRENCY_RATES.get(code, CURRENCY_RATES["USD"])
    return _decimal_money(amount * rate)


def _period_end(start: datetime, billing_cycle: str) -> datetime:
    return start + (timedelta(days=365) if billing_cycle == "yearly" else timedelta(days=31))


def _plan_price(plan: Plan, billing_cycle: str, currency: str) -> Decimal:
    amount = plan.price_yearly if billing_cycle == "yearly" else plan.price_monthly
    return _convert_amount(Decimal(amount or 0), currency)


def _unlimited(value: int | None) -> bool:
    return not value or value <= 0


async def ensure_billing_catalog(db: AsyncSession) -> None:
    result = await db.execute(select(Plan).where(Plan.code.in_([item.code for item in PLAN_SEEDS])))
    existing_plans = {item.code: item for item in result.scalars().all()}
    for seed in PLAN_SEEDS:
        plan = existing_plans.get(seed.code)
        if plan is None:
            plan = Plan(code=seed.code)
            db.add(plan)
        plan.name = seed.name
        plan.description = seed.description
        plan.price_monthly = seed.monthly
        plan.price_yearly = seed.yearly
        plan.currency = "CNY"
        plan.storage_quota = seed.storage_quota
        plan.ai_quota = seed.ai_quota
        plan.ai_request_quota = seed.ai_request_quota
        plan.member_limit = seed.member_limit
        plan.advanced_model_enabled = seed.advanced_model_enabled
        plan.enterprise_support_enabled = seed.enterprise_support_enabled
        plan.sort_order = seed.sort_order
        plan.features = seed.features
        plan.model_policy = seed.model_policy
        plan.payment_options = {
            "monthly": float(seed.monthly),
            "yearly": float(seed.yearly),
            "currencies": list(CURRENCY_RATES.keys()),
        }
        plan.locale_labels = {
            "zh-CN": seed.name,
            "en-US": {
                "free": "Free",
                "pro": "Pro",
                "team": "Team",
                "enterprise": "Enterprise",
            }[seed.code],
        }
        plan.status = "active"

    result = await db.execute(
        select(PaymentProviderConfig).where(PaymentProviderConfig.code.in_([item["code"] for item in PROVIDER_SEEDS]))
    )
    existing_providers = {item.code: item for item in result.scalars().all()}
    for seed in PROVIDER_SEEDS:
        provider = existing_providers.get(seed["code"])
        if provider is None:
            provider = PaymentProviderConfig(code=seed["code"])
            db.add(provider)
        provider.name = seed["name"]
        provider.provider_type = seed["provider_type"]
        provider.supported_currencies = seed["supported_currencies"]
        provider.supported_regions = seed["supported_regions"]
        provider.sort_order = seed["sort_order"]
        provider.active = True
        provider.sandbox = provider.provider_type == "mock"
        provider.meta = seed["meta"]

    await db.flush()


async def get_active_plan(db: AsyncSession, code: str) -> Plan:
    await ensure_billing_catalog(db)
    result = await db.execute(select(Plan).where(Plan.code == code, Plan.status == "active"))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="套餐不存在")
    return plan


async def ensure_workspace_subscription(db: AsyncSession, workspace: Workspace) -> Subscription:
    await ensure_billing_catalog(db)
    result = await db.execute(
        select(Subscription)
        .where(Subscription.workspace_id == workspace.id, Subscription.status.in_(["active", "trialing", "past_due"]))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    if subscription:
        return subscription

    plan = await get_active_plan(db, workspace.plan or "free")
    now = _now()
    subscription = Subscription(
        workspace_id=workspace.id,
        plan_id=plan.id,
        status="active",
        billing_cycle="monthly",
        provider="system",
        seats=1,
        started_at=now,
        expires_at=_period_end(now, "monthly"),
        current_period_start=now,
        current_period_end=_period_end(now, "monthly"),
        meta={"source": "auto_free"},
    )
    _apply_plan_to_workspace(workspace, plan)
    db.add(subscription)
    await db.flush()
    return subscription


def _apply_plan_to_workspace(workspace: Workspace, plan: Plan) -> None:
    workspace.plan = plan.code
    workspace.storage_quota = plan.storage_quota
    workspace.ai_quota = plan.ai_quota


def plan_payload(plan: Plan, *, billing_cycle: str = "monthly", currency: str = "CNY", locale: str = "zh-CN") -> dict:
    currency_code = currency.upper()
    amount = _plan_price(plan, billing_cycle, currency_code)
    return {
        "id": str(plan.id),
        "code": plan.code,
        "name": (plan.locale_labels or {}).get(locale) or plan.name,
        "displayName": plan.name,
        "description": plan.description,
        "currency": currency_code,
        "priceMonthly": float(_convert_amount(Decimal(plan.price_monthly or 0), currency_code)),
        "priceYearly": float(_convert_amount(Decimal(plan.price_yearly or 0), currency_code)),
        "selectedAmount": float(amount),
        "storageQuota": plan.storage_quota,
        "aiTokenQuota": plan.ai_quota,
        "aiRequestQuota": plan.ai_request_quota,
        "memberLimit": plan.member_limit,
        "advancedModelEnabled": plan.advanced_model_enabled,
        "enterpriseSupportEnabled": plan.enterprise_support_enabled,
        "features": plan.features or {},
        "modelPolicy": plan.model_policy or {},
        "sortOrder": plan.sort_order,
        "status": plan.status,
    }


async def list_plans(db: AsyncSession, *, billing_cycle: str = "monthly", currency: str = "CNY", locale: str = "zh-CN") -> list[dict]:
    await ensure_billing_catalog(db)
    result = await db.execute(select(Plan).where(Plan.status == "active").order_by(Plan.sort_order.asc(), Plan.created_at.asc()))
    return [plan_payload(item, billing_cycle=billing_cycle, currency=currency, locale=locale) for item in result.scalars().all()]


async def list_payment_providers(db: AsyncSession, *, currency: str | None = None, region: str | None = None) -> list[dict]:
    await ensure_billing_catalog(db)
    result = await db.execute(
        select(PaymentProviderConfig).where(PaymentProviderConfig.active.is_(True)).order_by(PaymentProviderConfig.sort_order.asc())
    )
    providers = []
    currency_code = currency.upper() if currency else None
    region_code = region.upper() if region else None
    for item in result.scalars().all():
        currencies = item.supported_currencies or []
        regions = item.supported_regions or []
        if currency_code and currency_code not in currencies:
            continue
        if region_code and region_code not in regions:
            continue
        providers.append(
            {
                "id": str(item.id),
                "code": item.code,
                "name": item.name,
                "type": item.provider_type,
                "supportedCurrencies": currencies,
                "supportedRegions": regions,
                "sandbox": item.sandbox,
                "metadata": item.meta or {},
            }
        )
    return providers


async def current_usage(db: AsyncSession, workspace: Workspace) -> dict:
    storage_used = await db.scalar(
        select(func.coalesce(func.sum(WorkspaceFile.size), 0)).where(
            WorkspaceFile.workspace_id == workspace.id,
            WorkspaceFile.deleted_at.is_(None),
        )
    )
    file_count = await db.scalar(
        select(func.count(WorkspaceFile.id)).where(WorkspaceFile.workspace_id == workspace.id, WorkspaceFile.deleted_at.is_(None))
    )
    member_count = await db.scalar(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.status == "active")
    )
    ai_tokens = await db.scalar(
        select(func.coalesce(func.sum(UsageRecord.quantity), Decimal("0"))).where(
            UsageRecord.workspace_id == workspace.id,
            UsageRecord.unit.in_(["token", "tokens"]),
        )
    )
    ai_requests = await db.scalar(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.workspace_id == workspace.id,
            UsageRecord.usage_type.in_(["ai_tokens", "file_ai.ask", "file_ai.summary", "knowledge.ask", "document.ai_write"]),
        )
    )
    return {
        "storageUsed": int(storage_used or 0),
        "fileCount": int(file_count or 0),
        "memberCount": int(member_count or 0),
        "aiTokensUsed": float(ai_tokens or 0),
        "aiRequestsUsed": int(ai_requests or 0),
    }


async def entitlement_payload(db: AsyncSession, workspace: Workspace) -> dict:
    subscription = await ensure_workspace_subscription(db, workspace)
    plan = await get_active_plan(db, workspace.plan or "free")
    usage = await current_usage(db, workspace)
    return {
        "workspace": {
            "id": str(workspace.id),
            "name": workspace.name,
            "plan": workspace.plan,
            "storageQuota": workspace.storage_quota,
            "aiQuota": workspace.ai_quota,
            "locale": workspace.locale,
        },
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status,
            "billingCycle": subscription.billing_cycle,
            "provider": subscription.provider,
            "seats": subscription.seats,
            "cancelAtPeriodEnd": subscription.cancel_at_period_end,
            "currentPeriodStart": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "currentPeriodEnd": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "expiresAt": subscription.expires_at.isoformat() if subscription.expires_at else None,
        },
        "plan": plan_payload(plan),
        "usage": usage,
        "limits": {
            "storageQuota": plan.storage_quota,
            "aiTokenQuota": plan.ai_quota,
            "aiRequestQuota": plan.ai_request_quota,
            "memberLimit": plan.member_limit,
            "advancedModelEnabled": plan.advanced_model_enabled,
            "enterpriseSupportEnabled": plan.enterprise_support_enabled,
        },
    }


async def create_checkout(
    db: AsyncSession,
    *,
    workspace: Workspace,
    user_id: uuid.UUID,
    plan_code: str,
    billing_cycle: str,
    currency: str,
    provider_code: str,
    locale: str,
    region: str,
    seats: int,
) -> dict:
    if billing_cycle not in {"monthly", "yearly"}:
        raise HTTPException(status_code=400, detail="账期只支持 monthly 或 yearly")
    currency_code = currency.upper()
    region_code = region.upper()
    plan = await get_active_plan(db, plan_code)
    providers = await list_payment_providers(db, currency=currency_code, region=region_code)
    provider = next((item for item in providers if item["code"] == provider_code), None)
    if provider is None:
        raise HTTPException(status_code=400, detail="当前地区或币种不支持该支付方式")

    subscription = await ensure_workspace_subscription(db, workspace)
    amount = _plan_price(plan, billing_cycle, currency_code)
    order_no = f"LM{_now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    order = Order(
        workspace_id=workspace.id,
        user_id=user_id,
        subscription_id=subscription.id,
        plan_id=plan.id,
        order_no=order_no,
        order_type="subscription",
        billing_cycle=billing_cycle,
        amount=amount,
        currency=currency_code,
        status="pending" if amount > 0 else "paid",
        payment_provider=provider_code,
        locale=locale,
        region=region_code,
        description=f"{plan.name} {billing_cycle}",
        paid_at=_now() if amount <= 0 else None,
        expires_at=_now() + timedelta(minutes=30),
        meta={"seats": seats, "planCode": plan.code, "provider": provider},
    )
    db.add(order)
    await db.flush()

    checkout_url = f"/billing/checkout/{order.order_no}"
    payment = Payment(
        order_id=order.id,
        provider=provider_code,
        provider_payment_id=f"{provider_code}_{order.order_no.lower()}",
        status=order.status,
        amount=amount,
        currency=currency_code,
        checkout_url=checkout_url,
        paid_at=order.paid_at,
        raw_payload={"provider": provider, "mode": "mock_checkout" if provider_code.startswith("mock") else "external_pending"},
    )
    db.add(payment)

    if amount <= 0:
        await activate_subscription(db, order=order)

    await db.flush()
    return {
        "order": order_payload(order),
        "payment": payment_payload(payment),
        "checkoutUrl": checkout_url,
        "mode": "mock" if provider_code.startswith("mock") else "external_placeholder",
    }


async def activate_subscription(db: AsyncSession, *, order: Order) -> Subscription:
    if not order.plan_id:
        raise HTTPException(status_code=400, detail="订单缺少套餐信息")
    result = await db.execute(select(Plan).where(Plan.id == order.plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="套餐不存在")

    result = await db.execute(select(Workspace).where(Workspace.id == order.workspace_id))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="工作区不存在")

    subscription = order.subscription or await ensure_workspace_subscription(db, workspace)
    now = _now()
    subscription.plan_id = plan.id
    subscription.status = "active"
    subscription.billing_cycle = order.billing_cycle
    subscription.provider = order.payment_provider or "mock_cn"
    subscription.seats = int((order.meta or {}).get("seats") or 1)
    subscription.cancel_at_period_end = False
    subscription.started_at = subscription.started_at or now
    subscription.expires_at = _period_end(now, order.billing_cycle)
    subscription.current_period_start = now
    subscription.current_period_end = subscription.expires_at
    subscription.meta = {"lastOrderNo": order.order_no, "currency": order.currency}
    _apply_plan_to_workspace(workspace, plan)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=order.user_id,
            action="billing.subscription.activate",
            resource_type="subscription",
            resource_id=subscription.id,
            meta={"orderNo": order.order_no, "planCode": plan.code},
        )
    )
    await db.flush()
    return subscription


async def complete_mock_payment(db: AsyncSession, *, workspace: Workspace, order_no: str) -> dict:
    result = await db.execute(select(Order).where(Order.workspace_id == workspace.id, Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "paid":
        payment = await _latest_payment(db, order.id)
        return {"order": order_payload(order), "payment": payment_payload(payment) if payment else None}
    if not (order.payment_provider or "").startswith("mock"):
        raise HTTPException(status_code=400, detail="当前订单不是本地模拟支付订单")

    now = _now()
    order.status = "paid"
    order.paid_at = now
    payment = await _latest_payment(db, order.id)
    if payment:
        payment.status = "paid"
        payment.paid_at = now
        payment.raw_payload = {**(payment.raw_payload or {}), "completedBy": "mock"}
    await activate_subscription(db, order=order)
    return {"order": order_payload(order), "payment": payment_payload(payment) if payment else None}


async def _latest_payment(db: AsyncSession, order_id: uuid.UUID) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


def order_payload(order: Order) -> dict:
    return {
        "id": str(order.id),
        "workspaceId": str(order.workspace_id),
        "subscriptionId": str(order.subscription_id) if order.subscription_id else None,
        "planId": str(order.plan_id) if order.plan_id else None,
        "userId": str(order.user_id) if order.user_id else None,
        "orderNo": order.order_no,
        "orderType": order.order_type,
        "billingCycle": order.billing_cycle,
        "amount": float(order.amount or 0),
        "currency": order.currency,
        "status": order.status,
        "paymentProvider": order.payment_provider,
        "description": order.description,
        "locale": order.locale,
        "region": order.region,
        "paidAt": order.paid_at.isoformat() if order.paid_at else None,
        "expiresAt": order.expires_at.isoformat() if order.expires_at else None,
        "createdAt": order.created_at.isoformat() if order.created_at else None,
        "metadata": order.meta or {},
    }


def payment_payload(payment: Payment) -> dict:
    return {
        "id": str(payment.id),
        "orderId": str(payment.order_id),
        "provider": payment.provider,
        "providerPaymentId": payment.provider_payment_id,
        "status": payment.status,
        "amount": float(payment.amount or 0),
        "currency": payment.currency,
        "checkoutUrl": payment.checkout_url,
        "paidAt": payment.paid_at.isoformat() if payment.paid_at else None,
        "metadata": payment.raw_payload or {},
    }


async def list_workspace_orders(db: AsyncSession, workspace: Workspace) -> list[dict]:
    result = await db.execute(select(Order).where(Order.workspace_id == workspace.id).order_by(Order.created_at.desc()).limit(100))
    return [order_payload(item) for item in result.scalars().all()]


async def cancel_subscription_at_period_end(db: AsyncSession, workspace: Workspace) -> dict:
    subscription = await ensure_workspace_subscription(db, workspace)
    subscription.cancel_at_period_end = True
    subscription.status = "active"
    await db.flush()
    return {
        "id": str(subscription.id),
        "status": subscription.status,
        "cancelAtPeriodEnd": subscription.cancel_at_period_end,
        "currentPeriodEnd": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
    }


async def assert_storage_quota(db: AsyncSession, workspace: Workspace, added_bytes: int) -> None:
    await ensure_workspace_subscription(db, workspace)
    plan = await get_active_plan(db, workspace.plan or "free")
    if _unlimited(plan.storage_quota):
        return
    usage = await current_usage(db, workspace)
    if usage["storageUsed"] + added_bytes > plan.storage_quota:
        raise HTTPException(status_code=402, detail="当前套餐存储额度不足，请升级套餐后继续上传。")


async def assert_ai_quota(db: AsyncSession, workspace: Workspace, estimated_tokens: int = 1, *, request_count: int = 1) -> None:
    await ensure_workspace_subscription(db, workspace)
    plan = await get_active_plan(db, workspace.plan or "free")
    usage = await current_usage(db, workspace)
    if not _unlimited(plan.ai_quota) and usage["aiTokensUsed"] + estimated_tokens > plan.ai_quota:
        raise HTTPException(status_code=402, detail="当前套餐 AI 调用额度不足，请升级套餐后继续使用。")
    if not _unlimited(plan.ai_request_quota) and usage["aiRequestsUsed"] + request_count > plan.ai_request_quota:
        raise HTTPException(status_code=402, detail="当前套餐 AI 请求次数不足，请升级套餐后继续使用。")


async def assert_member_quota(db: AsyncSession, workspace: Workspace) -> None:
    await ensure_workspace_subscription(db, workspace)
    plan = await get_active_plan(db, workspace.plan or "free")
    if _unlimited(plan.member_limit):
        return
    member_count = await db.scalar(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.status == "active")
    )
    if int(member_count or 0) >= plan.member_limit:
        raise HTTPException(status_code=402, detail="当前套餐团队成员数量已达上限，请升级套餐。")


async def assert_advanced_model_allowed(db: AsyncSession, workspace: Workspace, model_name: str | None) -> None:
    if not model_name:
        return
    await ensure_workspace_subscription(db, workspace)
    plan = await get_active_plan(db, workspace.plan or "free")
    advanced_models = set((plan.model_policy or {}).get("advancedModels") or [])
    if model_name in advanced_models and not plan.advanced_model_enabled:
        raise HTTPException(status_code=402, detail="当前套餐不支持高级模型，请升级团队版或企业版。")


async def enterprise_overview(db: AsyncSession) -> dict:
    await ensure_billing_catalog(db)
    workspace_count = await db.scalar(select(func.count(Workspace.id)))
    active_subscriptions = await db.scalar(select(func.count(Subscription.id)).where(Subscription.status == "active"))
    paid_orders = await db.scalar(select(func.count(Order.id)).where(Order.status == "paid"))
    pending_orders = await db.scalar(select(func.count(Order.id)).where(Order.status == "pending"))
    revenue = await db.scalar(select(func.coalesce(func.sum(Order.amount), Decimal("0"))).where(Order.status == "paid", Order.currency == "CNY"))
    plan_rows = await db.execute(
        select(Plan.code, Plan.name, func.count(Subscription.id))
        .join(Subscription, Subscription.plan_id == Plan.id, isouter=True)
        .group_by(Plan.code, Plan.name, Plan.sort_order)
        .order_by(Plan.sort_order.asc())
    )
    provider_rows = await db.execute(
        select(Payment.provider, Payment.status, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), Decimal("0")))
        .group_by(Payment.provider, Payment.status)
        .order_by(Payment.provider.asc(), Payment.status.asc())
    )
    return {
        "workspaceCount": int(workspace_count or 0),
        "activeSubscriptions": int(active_subscriptions or 0),
        "paidOrders": int(paid_orders or 0),
        "pendingOrders": int(pending_orders or 0),
        "revenueCny": float(revenue or 0),
        "plans": [{"code": code, "name": name, "subscriptions": int(count or 0)} for code, name, count in plan_rows.all()],
        "providers": [
            {"provider": provider, "status": status, "count": int(count or 0), "amount": float(amount or 0)}
            for provider, status, count, amount in provider_rows.all()
        ],
    }
