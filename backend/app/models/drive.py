import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Folder(Base):
    __tablename__ = 'folders'
    __table_args__ = (UniqueConstraint('workspace_id', 'parent_id', 'name', name='uq_folders_workspace_parent_name'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('folders.id', ondelete='SET NULL'), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    is_team_shared: Mapped[bool] = mapped_column(default=False)
    shared_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

    workspace = relationship('Workspace')
    parent = relationship('Folder', remote_side=[id])
    owner = relationship('User', foreign_keys=[owner_id])
    sharer = relationship('User', foreign_keys=[shared_by])
    files = relationship('WorkspaceFile', back_populates='folder')


class WorkspaceFile(Base):
    __tablename__ = 'files'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('folders.id', ondelete='SET NULL'), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    extension: Mapped[str] = mapped_column(String(32), default='', index=True)
    mime_type: Mapped[str] = mapped_column(String(160), default='application/octet-stream')
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_provider: Mapped[str] = mapped_column(String(50), default='local')
    bucket: Mapped[str | None] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    checksum: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(30), default='active', index=True)
    parse_status: Mapped[str] = mapped_column(String(30), default='pending', index=True)
    ai_status: Mapped[str] = mapped_column(String(30), default='not_ready', index=True)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    workspace = relationship('Workspace')
    owner = relationship('User', foreign_keys=[owner_id])
    folder = relationship('Folder', back_populates='files')
    versions = relationship('FileVersion', back_populates='file', cascade='all, delete-orphan')
    shares = relationship('FileShare', back_populates='file', cascade='all, delete-orphan')
    tags = relationship('FileTag', back_populates='file', cascade='all, delete-orphan')


class FileVersion(Base):
    __tablename__ = 'file_versions'
    __table_args__ = (UniqueConstraint('file_id', 'version_no', name='uq_file_versions_file_no'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('files.id', ondelete='CASCADE'), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    checksum: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship('WorkspaceFile', back_populates='versions')
    creator = relationship('User', foreign_keys=[created_by])


class FileShare(Base):
    __tablename__ = 'file_shares'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('files.id', ondelete='CASCADE'), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    share_type: Mapped[str] = mapped_column(String(30), default='link', index=True)
    permission: Mapped[str] = mapped_column(String(30), default='view')
    token: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship('WorkspaceFile', back_populates='shares')
    workspace = relationship('Workspace')
    creator = relationship('User', foreign_keys=[created_by])


class Tag(Base):
    __tablename__ = 'tags'
    __table_args__ = (UniqueConstraint('workspace_id', 'name', name='uq_tags_workspace_name'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(20), default="blue")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    files = relationship('FileTag', back_populates='tag', cascade='all, delete-orphan')


class FileTag(Base):
    __tablename__ = 'file_tags'
    __table_args__ = (UniqueConstraint('file_id', 'tag_id', name='uq_file_tags_file_tag'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspace_files.id', ondelete='CASCADE'), index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE'), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship('WorkspaceFile', back_populates='tags')
    tag = relationship('Tag', back_populates='files')
