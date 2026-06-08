import io
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.template import UserTemplate
from app.services.storage import get_storage
from app.utils.files import ALLOWED_TEMPLATE_EXTENSIONS, new_storage_key, secure_filename

router = APIRouter(prefix='/templates', tags=['templates'])


@router.get('', response_model=dict)
async def list_templates(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(UserTemplate).order_by(UserTemplate.created_at.desc()))
    items = result.scalars().all()
    return {
        'success': True,
        'templates': [
            {
                'id': str(item.id),
                'name': item.name,
                'filename': item.name,
                'size': item.size_bytes,
                'storageKey': item.storage_key,
            }
            for item in items
        ],
    }


@router.post('/upload', response_model=dict)
async def upload_template(
    file: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_session),
):
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail='没有选择模板文件')

    original = secure_filename(file.filename)
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_TEMPLATE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'不支持的模板格式: {ext}')

    data = await file.read()
    storage_key, _ = new_storage_key(original, prefix='templates')
    storage = get_storage()
    await storage.save(storage_key, data)

    record = UserTemplate(name=original, storage_key=storage_key, size_bytes=len(data))
    db.add(record)
    await db.flush()

    return {
        'success': True,
        'template': {
            'id': str(record.id),
            'name': record.name,
            'filename': record.name,
            'size': record.size_bytes,
            'storageKey': record.storage_key,
        },
    }


@router.get('/{template_id}/download')
async def download_template(template_id: str, db: AsyncSession = Depends(get_session)):
    import uuid

    try:
        tid = uuid.UUID(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='模板路径无效') from exc

    result = await db.execute(select(UserTemplate).where(UserTemplate.id == tid))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail='模板不存在')

    storage = get_storage()
    local = storage.get_local_path(item.storage_key)
    if local:
        return FileResponse(str(local), filename=item.name)
    data = await storage.read(item.storage_key)
    headers = {'Content-Disposition': f"attachment; filename*=UTF-8''{quote(item.name)}"}
    return StreamingResponse(io.BytesIO(data), media_type='application/octet-stream', headers=headers)


@router.delete('/{template_id}', response_model=dict)
async def delete_template(template_id: str, db: AsyncSession = Depends(get_session)):
    import uuid

    try:
        tid = uuid.UUID(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='模板路径无效') from exc

    result = await db.execute(select(UserTemplate).where(UserTemplate.id == tid))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail='模板不存在')

    storage = get_storage()
    await storage.delete(item.storage_key)
    await db.delete(item)
    return {'success': True}
