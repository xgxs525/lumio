import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Workspace(Base):
    __tablename__ = 'workspaces'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(50), default='free', index=True)
    storage_quota: Mapped[int] = mapped_column(BigInteger, default=10 * 1024 * 1024 * 1024)
    ai_quota: Mapped[int] = mapped_column(BigInteger, default=100000)
    locale: Mapped[str] = mapped_column(String(20), default='zh-CN')
    timezone: Mapped[str] = mapped_column(String(64), default='Asia/Shanghai')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship('User', back_populates='owned_workspaces', foreign_keys=[owner_id])
    members = relationship('WorkspaceMember', back_populates='workspace', cascade='all, delete-orphan')
    departments = relationship('Department', back_populates='workspace', cascade='all, delete-orphan')
    roles = relationship('Role', back_populates='workspace', cascade='all, delete-orphan')


class WorkspaceMember(Base):
    __tablename__ = 'workspace_members'
    __table_args__ = (UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_members_workspace_user'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('roles.id', ondelete='SET NULL'), nullable=True, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default='active', index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship('Workspace', back_populates='members')
    user = relationship('User', back_populates='workspace_memberships', foreign_keys=[user_id])
    role = relationship('Role', back_populates='members')
    department = relationship('Department', back_populates='members')


class Department(Base):
    __tablename__ = 'departments'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('departments.id', ondelete='SET NULL'), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship('Workspace', back_populates='departments')
    parent = relationship('Department', remote_side=[id])
    manager = relationship('User', foreign_keys=[manager_id])
    members = relationship('WorkspaceMember', back_populates='department')


class Role(Base):
    __tablename__ = 'roles'
    __table_args__ = (UniqueConstraint('workspace_id', 'code', name='uq_roles_workspace_code'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    workspace = relationship('Workspace', back_populates='roles')
    members = relationship('WorkspaceMember', back_populates='role')
    permissions = relationship('RolePermission', back_populates='role', cascade='all, delete-orphan')


class Permission(Base):
    __tablename__ = 'permissions'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    module: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    roles = relationship('RolePermission', back_populates='permission', cascade='all, delete-orphan')


class RolePermission(Base):
    __tablename__ = 'role_permissions'
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_pair'),)

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True
    )

    role = relationship('Role', back_populates='permissions')
    permission = relationship('Permission', back_populates='roles')
