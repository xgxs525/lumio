from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str
    filename: str
    filepath: str
    storage_key: str
    size: int


class ColumnsRequest(BaseModel):
    filepath: str | None = None
    storage_key: str | None = None
    header_row: int = Field(default=1, ge=1)
    auto_detect: bool = True


class ColumnsResponse(BaseModel):
    columns: list[str]
    header_row: int
