from typing import Any, Literal

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    filepath: str | None = None
    storage_key: str | None = None
    split_type: str = Field(alias='splitType', default='column')
    column: str | None = None
    rows_per_file: int | None = Field(default=None, alias='rowsPerFile')
    header_row: int = Field(default=1, alias='headerRow', ge=1)

    model_config = {'populate_by_name': True}


class SplitRequest(PreviewRequest):
    pass


class TaskCreateResponse(BaseModel):
    task_id: str = Field(alias='taskId')
    output_dir: str | None = Field(default=None, alias='outputDir')

    model_config = {'populate_by_name': True}


class TaskStatus(BaseModel):
    id: str
    status: Literal['pending', 'running', 'completed', 'failed']
    message: str = ''
    error: str | None = None
    split_type: str | None = None
    output_dir: str | None = None
    files: list[str] = []
    files_count: int = 0
    rows_processed: int = 0
    success: bool = False
    extra: dict[str, Any] = {}
