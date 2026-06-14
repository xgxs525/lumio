from pathlib import Path

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.file import UploadedFile
from app.models.user import User
from app.schemas.file import ColumnsRequest
from app.services.storage import get_storage
from app.utils.files import ALLOWED_UPLOAD_EXTENSIONS, new_storage_key, secure_filename

router = APIRouter(prefix="/files", tags=["files"])


async def _get_owned_uploaded_file(
    db: AsyncSession,
    user_id,
    storage_key: str | None,
) -> UploadedFile:
    if not storage_key:
        raise HTTPException(status_code=400, detail="请先上传文件")
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.storage_key == storage_key,
            UploadedFile.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return item


def _resolve_local_path(storage_key: str) -> Path:
    storage = get_storage()
    local = storage.get_local_path(storage_key)
    if local and local.is_file():
        return local
    raise HTTPException(status_code=400, detail="文件不存在")


@router.post("/upload", response_model=dict)
async def upload_file(
    file: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="没有文件")

    original_filename = secure_filename(file.filename)
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    data = await file.read()
    storage_key, _ = new_storage_key(original_filename, prefix=f"users/{user.id}/uploads")
    storage = get_storage()
    await storage.save(storage_key, data)

    record = UploadedFile(
        user_id=user.id,
        original_name=original_filename,
        storage_key=storage_key,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
    )
    db.add(record)
    await db.flush()

    local_path = storage.get_local_path(storage_key)
    filepath = str(local_path) if local_path else storage_key

    return {
        "success": True,
        "id": str(record.id),
        "filename": original_filename,
        "filepath": filepath,
        "storageKey": storage_key,
        "size": len(data),
    }


@router.post("/columns", response_model=dict)
async def get_columns(
    payload: ColumnsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    uploaded_file = await _get_owned_uploaded_file(db, user.id, payload.storage_key)
    path = _resolve_local_path(uploaded_file.storage_key)

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        header_row = payload.header_row

        def read_header_values(row_num: int) -> list:
            return [cell.value for cell in ws[row_num]]

        def clean_headers(values: list) -> list[str]:
            headers = []
            for value in values:
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    headers.append(text)
            return headers

        non_empty_headers = clean_headers(read_header_values(header_row))
        effective_header_row = header_row

        if payload.auto_detect and len(non_empty_headers) <= 1:
            best_header_row = header_row
            best_headers = non_empty_headers
            for candidate_row in range(header_row + 1, header_row + 11):
                candidate_headers = clean_headers(read_header_values(candidate_row))
                if len(candidate_headers) > len(best_headers):
                    best_header_row = candidate_row
                    best_headers = candidate_headers
            if len(best_headers) > len(non_empty_headers):
                effective_header_row = best_header_row
                non_empty_headers = best_headers

        wb.close()
        return {
            "success": True,
            "columns": non_empty_headers,
            "headerRow": effective_header_row,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
