import re
import uuid
from pathlib import Path
from urllib.parse import quote


ALLOWED_UPLOAD_EXTENSIONS = {
    '.xlsx', '.xls', '.xlsm', '.csv',
    '.doc', '.docx', '.ppt', '.pptx', '.pdf',
    '.txt', '.md', '.json', '.png', '.jpg', '.jpeg',
}
ALLOWED_TEMPLATE_EXTENSIONS = {
    '.xlsx', '.xls', '.xlsm', '.csv', '.doc', '.docx', '.ppt', '.pptx', '.pdf', '.txt', '.md',
    '.png', '.jpg', '.jpeg', '.webp',
}
ALLOWED_SPLIT_TYPES = {'column', 'row_count', 'sheet'}


def secure_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r'[^\w.\-]+', '_', name, flags=re.UNICODE).strip('._')
    return name[:180]


def safe_original_filename(filename: str | None, fallback: str = 'download', max_length: int = 180) -> str:
    raw = (filename or '').replace('\\', '/')
    name = Path(raw).name.strip()
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', '_', name, flags=re.UNICODE).strip(' ._')

    if not name:
        name = fallback

    suffix = Path(name).suffix
    if len(name) > max_length:
        stem = Path(name).stem[: max(1, max_length - len(suffix))]
        name = f'{stem}{suffix}'
    name = name.strip(' ._')
    if not name:
        name = 'download'
    return name


def download_content_disposition(filename: str | None, fallback: str = 'download') -> str:
    safe_name = safe_original_filename(filename, fallback=fallback, max_length=255)
    suffix = Path(safe_name).suffix
    ascii_stem = Path(safe_name).stem.encode('ascii', errors='ignore').decode('ascii').strip(' ._')
    ascii_name = f'{ascii_stem or fallback}{suffix}'
    ascii_name = safe_original_filename(ascii_name, fallback=fallback, max_length=255)
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(safe_name, safe="")}'


def new_storage_key(original_name: str, prefix: str = 'uploads') -> tuple[str, str]:
    ext = Path(original_name).suffix.lower()
    unique = uuid.uuid4().hex
    return f'{prefix}/{unique}{ext}', unique


def coerce_positive_int(value, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field_name}必须是大于0的整数') from exc
    if number <= 0:
        raise ValueError(f'{field_name}必须是大于0的整数')
    return number
