from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=('.env', '../.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = '序光'
    app_env: Literal['development', 'staging', 'production'] = 'development'
    debug: bool = True
    api_prefix: str = '/api/v1'
    cors_origins: str = 'http://localhost:3000,http://127.0.0.1:3000'

    # PostgreSQL
    database_url: str = 'postgresql+asyncpg://postgres:Xg022335@localhost:5432/lumio'
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    slow_request_seconds: float = 1.5

    # Redis / Celery
    redis_url: str = 'redis://localhost:6379/0'
    celery_broker_url: str = 'redis://localhost:6379/1'
    celery_result_backend: str = 'redis://localhost:6379/2'

    # Storage: local | oss
    storage_backend: Literal['local', 'oss'] = 'local'
    local_storage_path: str = './storage'
    oss_endpoint: str = ''
    oss_access_key_id: str = ''
    oss_access_key_secret: str = ''
    oss_bucket_name: str = ''
    oss_base_url: str = ''

    # AI Gateway (OpenAI-compatible chat completions) — 默认对接 DeepSeek
    ai_gateway_base_url: str = 'https://api.deepseek.com/v1'
    ai_gateway_api_key: str = ''
    ai_gateway_model: str = 'deepseek-chat'
    ai_gateway_timeout: int = 120

    # Embedding Gateway (OpenAI-compatible embeddings). Empty key uses local vectors.
    embedding_base_url: str = 'https://api.openai.com/v1'
    embedding_api_key: str = ''
    embedding_model: str = 'text-embedding-3-small'
    embedding_dimensions: int = 128

    # External provider adapters. Empty keys keep local mock mode enabled.
    sms_provider: str = 'mock'
    sms_api_key: str = ''
    email_provider: str = 'mock'
    email_api_key: str = ''
    payment_provider: str = 'mock'

    # Security
    secret_key: str = 'change-me-in-production'
    access_token_expire_minutes: int = 60 * 24 * 7

    max_upload_size_mb: int = 500

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

