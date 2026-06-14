import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = 'documents'

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
    title: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_text: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(30), default='draft', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    workspace = relationship('Workspace')
    owner = relationship('User', foreign_keys=[owner_id])
    folder = relationship('Folder')
    versions = relationship('DocumentVersion', back_populates='document', cascade='all, delete-orphan')
    shares = relationship('DocumentShare', back_populates='document', cascade='all, delete-orphan')


class DocumentVersion(Base):
    __tablename__ = 'document_versions'
    __table_args__ = (UniqueConstraint('document_id', 'version_no', name='uq_document_versions_document_no'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_text: Mapped[str] = mapped_column(Text, default='')
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship('Document', back_populates='versions')
    creator = relationship('User', foreign_keys=[created_by])


class DocumentShare(Base):
    __tablename__ = 'document_shares'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), index=True
    )
    share_type: Mapped[str] = mapped_column(String(30), default='link', index=True)
    permission: Mapped[str] = mapped_column(String(30), default='view')
    token: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document = relationship('Document', back_populates='shares')
    creator = relationship('User', foreign_keys=[created_by])
