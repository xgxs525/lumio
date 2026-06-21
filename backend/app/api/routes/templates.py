from __future__ import annotations

import io
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.template import UserTemplate
from app.models.user import User
from app.services.storage import get_storage
from app.utils.files import ALLOWED_TEMPLATE_EXTENSIONS, new_storage_key, secure_filename

router = APIRouter(prefix="/templates", tags=["templates"])


def _template_payload(item: UserTemplate) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "filename": item.name,
        "size": item.size_bytes,
        "storageKey": item.storage_key,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
        "downloadUrl": f"/api/v1/templates/{item.id}/download",
    }


async def _get_template_for_user(db: AsyncSession, template_id: str, user: User) -> UserTemplate:
    try:
        tid = uuid.UUID(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="模板 ID 无效") from exc

    result = await db.execute(
        select(UserTemplate).where(
            UserTemplate.id == tid,
            or_(UserTemplate.user_id == user.id, UserTemplate.user_id.is_(None)),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return item


@router.get("", response_model=dict)
async def list_public_templates(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(UserTemplate).where(UserTemplate.user_id.is_(None)).order_by(UserTemplate.created_at.desc()).limit(60)
    )
    return {"success": True, "templates": [_template_payload(item) for item in result.scalars().all()]}


@router.get("/mine", response_model=dict)
async def list_my_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(UserTemplate).where(UserTemplate.user_id == user.id).order_by(UserTemplate.created_at.desc()).limit(100)
    )
    return {"success": True, "templates": [_template_payload(item) for item in result.scalars().all()]}


@router.post("/upload", response_model=dict)
async def upload_template(
    file: UploadFile | None = File(default=None),
    name: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="请选择要上传的模板文件")

    original = secure_filename(file.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_TEMPLATE_EXTENSIONS:
        allowed = "、".join(sorted(ALLOWED_TEMPLATE_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"不支持的模板格式：{ext}，支持 {allowed}")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="模板文件为空")

    storage_key, _ = new_storage_key(original, prefix=f"users/{user.id}/templates")
    storage = get_storage()
    await storage.save(storage_key, data)

    display_name = (name or original).strip() or original
    record = UserTemplate(
        user_id=user.id,
        name=display_name[:255],
        storage_key=storage_key,
        size_bytes=len(data),
    )
    db.add(record)
    await db.flush()

    return {"success": True, "template": _template_payload(record)}


@router.get("/{template_id}/download")
async def download_template(
    template_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    item = await _get_template_for_user(db, template_id, user)
    storage = get_storage()
    local = storage.get_local_path(item.storage_key)
    if local:
        return FileResponse(str(local), filename=item.name)

    data = await storage.read(item.storage_key)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(item.name)}"}
    return StreamingResponse(io.BytesIO(data), media_type="application/octet-stream", headers=headers)


@router.delete("/{template_id}", response_model=dict)
async def delete_template(
    template_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    item = await _get_template_for_user(db, template_id, user)
    if item.user_id != user.id:
        raise HTTPException(status_code=403, detail="不能删除系统模板")

    storage = get_storage()
    await storage.delete(item.storage_key)
    await db.delete(item)
    return {"success": True}
