import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.models.task import ProcessingTask
from app.services.excel import get_excel_splitter, get_logger
from app.services.storage import get_storage

settings = get_settings()
sync_engine = create_engine(settings.database_url.replace('postgresql+asyncpg', 'postgresql+psycopg2'))
SyncSession = sessionmaker(sync_engine)


def _update_task(task_id: str, **fields):
    with SyncSession() as session:
        task = session.get(ProcessingTask, uuid.UUID(task_id))
        if not task:
            return
        for key, value in fields.items():
            setattr(task, key, value)
        session.commit()


@celery_app.task(bind=True, name='excel.split')
def run_split_task(
    self,
    task_id: str,
    storage_key: str,
    split_type: str,
    column: str | None = None,
    rows_per_file: int | None = None,
    header_row: int = 1,
):
    logger = get_logger()
    splitter = get_excel_splitter()
    storage = get_storage()

    _update_task(task_id, status='running', message='开始拆分...', celery_task_id=self.request.id)

    async def _read_file():
        return await storage.read(storage_key)

    try:
        file_bytes = asyncio.run(_read_file())
    except Exception as exc:
        _update_task(task_id, status='failed', error=str(exc), message='读取文件失败')
        return {'success': False, 'error': str(exc)}

    work_dir = Path(settings.local_storage_path) / 'tasks' / task_id
    work_dir.mkdir(parents=True, exist_ok=True)
    input_path = work_dir / Path(storage_key).name
    input_path.write_bytes(file_bytes)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = work_dir / f'output_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if split_type == 'column':
            result = splitter.split_by_column(
                str(input_path), str(output_dir), column,
                header_row=header_row, create_subdir=False,
            )
        elif split_type == 'row_count':
            result = splitter.split_by_row_count(
                str(input_path), str(output_dir), int(rows_per_file),
                header_row=header_row, create_subdir=False,
            )
        elif split_type == 'sheet':
            result = splitter.split_by_sheet(
                str(input_path), str(output_dir),
                header_row=header_row, create_subdir=False,
            )
        else:
            raise ValueError(f'未知拆分类型: {split_type}')

        files = result.files_created or []
        _update_task(
            task_id,
            status='completed' if result.success else 'failed',
            message=splitter.generate_report(result),
            output_dir=str(output_dir),
            result_files=files,
            files_count=result.files_count,
            rows_processed=result.rows_processed,
            error=result.error_message if not result.success else None,
        )
        return {
            'success': result.success,
            'files_count': result.files_count,
            'rows_processed': result.rows_processed,
        }
    except Exception as exc:
        logger.exception('拆分任务失败: %s', task_id)
        _update_task(task_id, status='failed', error=str(exc), message='拆分失败')
        return {'success': False, 'error': str(exc)}
