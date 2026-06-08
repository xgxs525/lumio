import re
import uuid
from pathlib import Path


ALLOWED_UPLOAD_EXTENSIONS = {
    '.xlsx', '.xls', '.xlsm', '.csv',
    '.doc', '.docx', '.ppt', '.pptx', '.pdf',
    '.txt', '.md', '.png', '.jpg', '.jpeg',
}
ALLOWED_TEMPLATE_EXTENSIONS = {
    '.xlsx', '.xls', '.xlsm', '.csv', '.doc', '.docx', '.ppt', '.pptx', '.pdf', '.txt', '.md',
}
ALLOWED_SPLIT_TYPES = {'column', 'row_count', 'sheet'}


def secure_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r'[^\w.\-]+', '_', name, flags=re.UNICODE).strip('._')
    return name[:180]


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
