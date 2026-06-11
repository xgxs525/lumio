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
    database_url: str = 'postgresql+psycopg://lumio:lumio@localhost:5432/lumio'

    # Redis
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

    # AI Gateway
    ai_gateway_base_url: str = 'https://api.openai.com/v1'
    ai_gateway_api_key: str = ''
    ai_gateway_model: str = 'gpt-4o-mini'
    ai_gateway_timeout: int = 60

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
