import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default='')
    name: Mapped[str] = mapped_column(String(100), default='')
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    locale: Mapped[str] = mapped_column(String(20), default='zh-CN')
    timezone: Mapped[str] = mapped_column(String(64), default='Asia/Shanghai')
    status: Mapped[str] = mapped_column(String(30), default='active', index=True)

    # Legacy compatibility fields kept until auth routes are fully migrated.
    nickname: Mapped[str] = mapped_column(String(100), default='')
    hashed_password: Mapped[str] = mapped_column(String(255), default='')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    files = relationship('UploadedFile', back_populates='owner')
    tasks = relationship('ProcessingTask', back_populates='owner')
    templates = relationship('UserTemplate', back_populates='owner')
    owned_workspaces = relationship('Workspace', back_populates='owner', foreign_keys='Workspace.owner_id')
    workspace_memberships = relationship('WorkspaceMember', back_populates='user', foreign_keys='WorkspaceMember.user_id')
    auth_accounts = relationship('AuthAccount', back_populates='user', cascade='all, delete-orphan')
    sessions = relationship('UserSession', back_populates='user', cascade='all, delete-orphan')


class AuthAccount(Base):
    __tablename__ = 'auth_accounts'
    __table_args__ = (UniqueConstraint('provider', 'provider_user_id', name='uq_auth_accounts_provider_user'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), index=True
    )
    provider: Mapped[str] = mapped_column(String(60), index=True)
    provider_user_id: Mapped[str] = mapped_column(String(255), index=True)
    union_id: Mapped[str | None] = mapped_column(String(255), index=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship('User', back_populates='auth_accounts')


class UserSession(Base):
    __tablename__ = 'user_sessions'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User', back_populates='sessions')


class PasswordReset(Base):
    __tablename__ = 'password_resets'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), index=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    code: Mapped[str | None] = mapped_column(String(8))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User')
