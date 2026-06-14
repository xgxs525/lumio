from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.user import User
from app.services.billing import (
    cancel_subscription_at_period_end,
    activate_subscription,
    complete_mock_payment,
    create_checkout,
    enterprise_overview,
    entitlement_payload,
    list_payment_providers,
    list_plans,
    list_workspace_orders,
    order_payload,
    payment_payload,
)
from app.models.billing import Order, Payment
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_code: str = Field(..., min_length=1, max_length=80)
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    provider: str = Field(default="mock_cn", max_length=80)
    locale: str = Field(default="zh-CN", max_length=20)
    region: str = Field(default="CN", max_length=40)
    seats: int = Field(default=1, ge=1, le=10000)


@router.get("/plans", response_model=dict)
async def billing_plans(
    billing_cycle: str = "monthly",
    currency: str = "CNY",
    locale: str = "zh-CN",
    db: AsyncSession = Depends(get_session),
):
    plans = await list_plans(db, billing_cycle=billing_cycle, currency=currency, locale=locale)
    return {"success": True, "data": plans}


@router.get("/providers", response_model=dict)
async def billing_providers(
    currency: str | None = None,
    region: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    providers = await list_payment_providers(db, currency=currency, region=region)
    return {"success": True, "data": providers}


@router.get("/current", response_model=dict)
async def billing_current(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    return {"success": True, "data": await entitlement_payload(db, workspace)}


@router.get("/orders", response_model=dict)
async def billing_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    return {"success": True, "data": await list_workspace_orders(db, workspace)}


@router.get("/orders/{order_no}", response_model=dict)
async def billing_order_detail(
    order_no: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    order = await db.scalar(
        select(Order).where(Order.workspace_id == workspace.id, Order.order_no == order_no)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc()).limit(1)
    )
    return {
        "success": True,
        "data": {
            "order": order_payload(order),
            "payment": payment_payload(payment) if payment else None,
        },
    }


@router.post("/checkout", response_model=dict)
async def billing_checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    data = await create_checkout(
        db,
        workspace=workspace,
        user_id=user.id,
        plan_code=payload.plan_code,
        billing_cycle=payload.billing_cycle,
        currency=payload.currency,
        provider_code=payload.provider,
        locale=payload.locale,
        region=payload.region,
        seats=payload.seats,
    )
    return {"success": True, "data": data}


@router.post("/mock-pay/{order_no}", response_model=dict)
async def billing_mock_pay(
    order_no: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    return {"success": True, "data": await complete_mock_payment(db, workspace=workspace, order_no=order_no)}


@router.post("/webhooks/{provider}", response_model=dict)
async def billing_webhook(provider: str, request: Request, db: AsyncSession = Depends(get_session)):
    payload = await request.json()
    order_no = str(payload.get("order_no") or payload.get("orderNo") or "")
    event_status = str(payload.get("status") or payload.get("trade_status") or payload.get("type") or "received")
    if not order_no:
        return {
            "success": True,
            "data": {
                "accepted": True,
                "provider": provider,
                "mode": "placeholder",
                "message": "已接收回调；真实支付接入后需要按服务商规则验签。",
            },
        }

    order = await db.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    payment = await db.scalar(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc()).limit(1)
    )
    if event_status.lower() in {"paid", "success", "trade_success", "checkout.session.completed"}:
        now = datetime.now(UTC)
        order.status = "paid"
        order.paid_at = now
        if payment:
            payment.status = "paid"
            payment.paid_at = now
            payment.raw_payload = payload
        await activate_subscription(db, order=order)
        status_text = "paid"
    else:
        if payment:
            payment.raw_payload = payload
        status_text = order.status
    await db.flush()
    return {
        "success": True,
        "data": {
            "accepted": True,
            "provider": provider,
            "orderNo": order.order_no,
            "status": status_text,
            "mode": "mock_verified" if provider.startswith("mock") else "signature_pending",
        },
    }


@router.post("/subscription/cancel", response_model=dict)
async def billing_cancel_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    return {"success": True, "data": await cancel_subscription_at_period_end(db, workspace)}


@router.get("/enterprise/overview", response_model=dict)
async def billing_enterprise_overview(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return {"success": True, "data": await enterprise_overview(db)}
