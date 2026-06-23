"""Knowledge base models — kb_ prefix tables."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BIGINT, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KbKnowledgeBase(Base):
    __tablename__ = "kb_knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    visibility: Mapped[str] = mapped_column(String(32), default="private", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    default_model_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    embedding_model_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))

    source_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sources: Mapped[list["KbSource"]] = relationship(back_populates="knowledge_base", lazy="selectin")


class KbSource(Base):
    __tablename__ = "kb_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kb_knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # uploaded_file / cloud_file / document / web_url / pasted_text / manual

    file_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    url: Mapped[str | None] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_mime_type: Mapped[str | None] = mapped_column(String(128))
    file_size: Mapped[int | None] = mapped_column(BIGINT)
    raw_text: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    knowledge_base: Mapped[KbKnowledgeBase] = relationship(back_populates="sources")
    chunks: Mapped[list["KbChunk"]] = relationship(back_populates="source", lazy="selectin")


class KbChunk(Base):
    __tablename__ = "kb_chunks"
    __table_args__ = (UniqueConstraint("source_id", "chunk_index"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kb_knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kb_sources.id", ondelete="CASCADE"), nullable=False, index=True)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)

    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    page_number: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(255))
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(32), default="active")

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    knowledge_base: Mapped[KbKnowledgeBase] = relationship()
    source: Mapped[KbSource] = relationship(back_populates="chunks")
    embeddings: Mapped[list["KbChunkEmbedding"]] = relationship(back_populates="chunk", lazy="selectin")


class KbChunkEmbedding(Base):
    __tablename__ = "kb_chunk_embeddings"
    __table_args__ = (UniqueConstraint("chunk_id", "embedding_model_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kb_chunks.id", ondelete="CASCADE"), nullable=False, index=True)

    embedding_model_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    embedding_model_name: Mapped[str | None] = mapped_column(String(128))

    # For pgvector: embedding vector(1536)
    # For external stores: use vector_store + vector_id
    embedding: Mapped[list | None] = mapped_column(JSONB, default=list)

    vector_store: Mapped[str | None] = mapped_column(String(64))
    vector_collection: Mapped[str | None] = mapped_column(String(128))
    vector_id: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(String(32), default="ready")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chunk: Mapped[KbChunk] = relationship(back_populates="embeddings")


class KbQaRecord(Base):
    __tablename__ = "kb_qa_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("kb_knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)

    model_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    model_name: Mapped[str | None] = mapped_column(String(128))

    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=5)
    similarity_threshold: Mapped[float | None] = mapped_column(Float)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    quota_used: Mapped[float | None] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(32), default="completed")

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
