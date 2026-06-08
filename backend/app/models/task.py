import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProcessingTask(Base):
    __tablename__ = 'processing_tasks'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True
    )
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey('uploaded_files.id'), nullable=True, index=True
    )
    task_type: Mapped[str] = mapped_column(String(50), default='split')
    status: Mapped[str] = mapped_column(String(30), default='pending', index=True)
    split_type: Mapped[str | None] = mapped_column(String(30))
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    message: Mapped[str] = mapped_column(Text, default='')
    error: Mapped[str | None] = mapped_column(Text)
    output_dir: Mapped[str | None] = mapped_column(String(512))
    result_files: Mapped[list] = mapped_column(JSONB, default=list)
    files_count: Mapped[int] = mapped_column(Integer, default=0)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship('User', back_populates='tasks')
    source_file = relationship('UploadedFile', back_populates='tasks')
