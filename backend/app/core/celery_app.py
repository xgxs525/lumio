from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    'xuguang',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks.excel_tasks'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 30,
    worker_prefetch_multiplier=1,
)
