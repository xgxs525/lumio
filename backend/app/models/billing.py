import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plan(Base):
    __tablename__ = 'plans'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    price_yearly: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(20), default='CNY')
    storage_quota: Mapped[int] = mapped_column(BigInteger, default=0)
    ai_quota: Mapped[int] = mapped_column(BigInteger, default=0)
    ai_request_quota: Mapped[int] = mapped_column(BigInteger, default=0)
    member_limit: Mapped[int] = mapped_column(Integer, default=1)
    advanced_model_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    enterprise_support_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    model_policy: Mapped[dict] = mapped_column(JSONB, default=dict)
    payment_options: Mapped[dict] = mapped_column(JSONB, default=dict)
    locale_labels: Mapped[dict] = mapped_column(JSONB, default=dict)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(30), default='active', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    subscriptions = relationship('Subscription', back_populates='plan')


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('plans.id', ondelete='SET NULL'), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(40), default='active', index=True)
    billing_cycle: Mapped[str] = mapped_column(String(30), default='monthly')
    provider: Mapped[str] = mapped_column(String(80), default='mock_cn')
    seats: Mapped[int] = mapped_column(Integer, default=1)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace = relationship('Workspace')
    plan = relationship('Plan', back_populates='subscriptions')
    orders = relationship('Order', back_populates='subscription')


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True, index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('plans.id', ondelete='SET NULL'), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    order_no: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    order_type: Mapped[str] = mapped_column(String(40), default='subscription')
    billing_cycle: Mapped[str] = mapped_column(String(30), default='monthly')
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(20), default='CNY')
    status: Mapped[str] = mapped_column(String(40), default='pending', index=True)
    payment_provider: Mapped[str | None] = mapped_column(String(80))
    provider_order_id: Mapped[str | None] = mapped_column(String(180), index=True)
    locale: Mapped[str] = mapped_column(String(20), default='zh-CN')
    region: Mapped[str] = mapped_column(String(40), default='CN')
    description: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship('Workspace')
    user = relationship('User', foreign_keys=[user_id])
    plan = relationship('Plan')
    subscription = relationship('Subscription', back_populates='orders')
    payments = relationship('Payment', back_populates='order')


class Payment(Base):
    __tablename__ = 'payments'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('orders.id', ondelete='CASCADE'), index=True
    )
    provider: Mapped[str] = mapped_column(String(80), default='mock_cn', index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(40), default='pending', index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(20), default='CNY')
    checkout_url: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order = relationship('Order', back_populates='payments')


class PaymentProviderConfig(Base):
    __tablename__ = 'payment_provider_configs'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(40), default='mock')
    supported_currencies: Mapped[list] = mapped_column(JSONB, default=list)
    supported_regions: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sandbox: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
