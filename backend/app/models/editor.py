"""Rich-text editor models for knowledge base source creation."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BIGINT, DateTime, ForeignKey, Integer, String, Text, Uuid, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EditorDocument(Base):
    """Stores a rich-text document (manual entry or pasted text)."""

    __tablename__ = "editor_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(String(64), default="kb_source", index=True)

    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    # Generated content for different use-cases
    content_text: Mapped[str | None] = mapped_column(Text)      # plain text for retrieval
    content_markdown: Mapped[str | None] = mapped_column(Text)  # markdown for AI processing
    content_html: Mapped[str | None] = mapped_column(Text)      # html for display

    block_count: Mapped[int] = mapped_column(Integer, default=0)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    blocks: Mapped[list["EditorBlock"]] = relationship(back_populates="document", lazy="selectin", cascade="all, delete-orphan")


class EditorBlock(Base):
    """Core content block table — stores headings, paragraphs, images, code, etc."""

    __tablename__ = "editor_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("editor_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_block_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("editor_blocks.id", ondelete="CASCADE"), index=True)

    block_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    content: Mapped[dict] = mapped_column(JSONB, default=dict)  # {text, url, src, ...}
    plain_text: Mapped[str | None] = mapped_column(Text)
    style: Mapped[dict] = mapped_column("style", JSONB, default=dict)  # {color, bgColor, align, ...}
    attrs: Mapped[dict] = mapped_column("attrs", JSONB, default=dict)

    status: Mapped[str] = mapped_column(String(32), default="active")

    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document: Mapped[EditorDocument] = relationship(back_populates="blocks")
    assets: Mapped[list["EditorBlockAsset"]] = relationship(back_populates="block", lazy="selectin")


class EditorBlockAsset(Base):
    """Assets for editor blocks — images, files, videos."""

    __tablename__ = "editor_block_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("editor_blocks.id", ondelete="CASCADE"), nullable=False, index=True)

    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    url: Mapped[str | None] = mapped_column(Text)

    filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(BIGINT)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    block: Mapped[EditorBlock] = relationship(back_populates="assets")


class KbSourceEditorBinding(Base):
    """Links a kb_sources record to its editor_document origin."""

    __tablename__ = "kb_source_editor_bindings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kb_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("editor_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
