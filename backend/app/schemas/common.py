from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: str | None = None


class MessageResponse(BaseModel):
    message: str


class DictResponse(BaseModel):
    success: bool = True
    error: str | None = None
    extra: dict[str, Any] = {}
