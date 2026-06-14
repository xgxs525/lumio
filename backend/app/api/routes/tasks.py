import io
import os
import uuid
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.file import UploadedFile
from app.models.task import ProcessingTask
from app.models.user import User
from app.schemas.task import PreviewRequest, SplitRequest
from app.services.preview import preview_split as build_split_preview
from app.services.storage import get_storage
from app.tasks.excel_tasks import run_split_task
from app.utils.files import ALLOWED_SPLIT_TYPES, coerce_positive_int

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get_owned_uploaded_file(
    db: AsyncSession,
    user_id: uuid.UUID,
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


def _validate_split_payload(data: PreviewRequest) -> dict:
    split_type = data.split_type
    if split_type not in ALLOWED_SPLIT_TYPES:
        raise HTTPException(status_code=400, detail="未知拆分类型")
    if split_type == "column" and not data.column:
        raise HTTPException(status_code=400, detail="请指定拆分列")
    rows_per_file = data.rows_per_file
    if split_type == "row_count":
        try:
            rows_per_file = coerce_positive_int(rows_per_file, "每个文件行数")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        header_row = coerce_positive_int(data.header_row, "表头行")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "split_type": split_type,
        "column": data.column,
        "rows_per_file": rows_per_file,
        "header_row": header_row,
    }


@router.post("/preview", response_model=dict)
async def preview_split_task(
    data: PreviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    uploaded_file = await _get_owned_uploaded_file(db, user.id, data.storage_key)
    params = _validate_split_payload(data)
    storage = get_storage()
    local = storage.get_local_path(uploaded_file.storage_key)
    if not local or not local.is_file():
        raise HTTPException(status_code=400, detail="文件不存在")

    try:
        preview_result = build_split_preview(
            str(local),
            params["split_type"],
            column=params["column"],
            rows_per_file=params["rows_per_file"],
            header_row=params["header_row"],
        )
        return preview_result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/split", response_model=dict)
async def create_split_task(
    data: SplitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    uploaded_file = await _get_owned_uploaded_file(db, user.id, data.storage_key)
    params = _validate_split_payload(data)
    storage = get_storage()
    if not await storage.exists(uploaded_file.storage_key):
        raise HTTPException(status_code=400, detail="文件不存在")

    task = ProcessingTask(
        user_id=user.id,
        source_file_id=uploaded_file.id,
        task_type="split",
        status="pending",
        message="等待处理...",
        split_type=params["split_type"],
        params={
            "storage_key": uploaded_file.storage_key,
            "column": params["column"],
            "rows_per_file": params["rows_per_file"],
            "header_row": params["header_row"],
        },
    )
    db.add(task)
    await db.flush()

    celery_result = run_split_task.delay(
        str(task.id),
        uploaded_file.storage_key,
        params["split_type"],
        column=params["column"],
        rows_per_file=params["rows_per_file"],
        header_row=params["header_row"],
    )
    task.celery_task_id = celery_result.id
    await db.flush()

    return {
        "success": True,
        "taskId": str(task.id),
        "outputDir": None,
    }


@router.get("/{task_id}", response_model=dict)
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    task = await _get_task(db, task_id, user.id)

    return {
        "success": True,
        "task": {
            "id": str(task.id),
            "status": task.status,
            "message": task.message,
            "error": task.error,
            "split_type": task.split_type,
            "output_dir": task.output_dir,
            "files": task.result_files or [],
            "files_count": task.files_count,
            "rows_processed": task.rows_processed,
            "success": task.status == "completed" and not task.error,
        },
    }


def _safe_join(base_dir: str, filename: str) -> Path | None:
    try:
        base_path = Path(base_dir).resolve()
        target_path = (base_path / filename).resolve()
        target_path.relative_to(base_path)
        return target_path
    except (TypeError, ValueError, OSError):
        return None


@router.get("/{task_id}/download/{filename}")
async def download_file(
    task_id: str,
    filename: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    task = await _get_task(db, task_id, user.id)
    if not task.output_dir:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_path = _safe_join(task.output_dir, filename)
    if not file_path or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(str(file_path), filename=filename)


@router.get("/{task_id}/download-all")
async def download_all(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    task = await _get_task(db, task_id, user.id)
    files = task.result_files or []
    if not files:
        raise HTTPException(status_code=400, detail="没有生成的文件")

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            if os.path.exists(file_path):
                zf.write(file_path, os.path.basename(file_path))
    memory_file.seek(0)
    zip_name = f"{task_id}_split_results.zip"
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(zip_name)}"}
    return StreamingResponse(memory_file, media_type="application/zip", headers=headers)


async def _get_task(db: AsyncSession, task_id: str, user_id: uuid.UUID) -> ProcessingTask:
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="任务不存在") from exc
    result = await db.execute(
        select(ProcessingTask).where(ProcessingTask.id == task_uuid, ProcessingTask.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
