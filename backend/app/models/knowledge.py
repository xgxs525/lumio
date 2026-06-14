import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KnowledgeBase(Base):
    __tablename__ = 'knowledge_bases'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(40), default='private', index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace = relationship('Workspace')
    creator = relationship('User', foreign_keys=[created_by])
    sources = relationship('KnowledgeSource', back_populates='knowledge_base', cascade='all, delete-orphan')


class KnowledgeSource(Base):
    __tablename__ = 'knowledge_sources'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), index=True
    )
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    sync_status: Mapped[str] = mapped_column(String(40), default='pending', index=True)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    knowledge_base = relationship('KnowledgeBase', back_populates='sources')


class FileChunk(Base):
    __tablename__ = 'file_chunks'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('files.id', ondelete='CASCADE'), nullable=True, index=True
    )
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    source_type: Mapped[str] = mapped_column(String(40), default='file', index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(80), default='text')
    page_no: Mapped[int | None] = mapped_column(Integer)
    sheet_name: Mapped[str | None] = mapped_column(String(255))
    row_start: Mapped[int | None] = mapped_column(Integer)
    row_end: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column('metadata', JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship('WorkspaceFile')
    knowledge_base = relationship('KnowledgeBase')
    workspace = relationship('Workspace')
    embeddings = relationship('FileEmbedding', back_populates='chunk', cascade='all, delete-orphan')


class FileEmbedding(Base):
    __tablename__ = 'file_embeddings'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True
    )
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('files.id', ondelete='CASCADE'), nullable=True, index=True
    )
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(40), default='file', index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('file_chunks.id', ondelete='CASCADE'), nullable=True, index=True
    )
    embedding_model: Mapped[str] = mapped_column(String(120))
    # Stored as JSONB for local compatibility. Swap to pgvector when the extension is installed.
    embedding: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace = relationship('Workspace')
    file = relationship('WorkspaceFile')
    knowledge_base = relationship('KnowledgeBase')
    chunk = relationship('FileChunk', back_populates='embeddings')
