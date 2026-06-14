from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings

try:
    import oss2
except ImportError:
    oss2 = None


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> str:
        ...

    @abstractmethod
    async def read(self, key: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def get_local_path(self, key: str) -> Path | None:
        ...

    @abstractmethod
    def public_url(self, key: str) -> str | None:
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self.base_path / key).resolve()
        path.relative_to(self.base_path.resolve())
        return path

    async def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    async def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    async def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def get_local_path(self, key: str) -> Path | None:
        path = self._resolve(key)
        return path if path.is_file() else None

    def public_url(self, key: str) -> str | None:
        return None


class OSSStorageBackend(StorageBackend):
    def __init__(self):
        settings = get_settings()
        if oss2 is None:
            raise RuntimeError('oss2 is required for OSS storage backend')
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
        self.base_url = settings.oss_base_url.rstrip('/')

    async def save(self, key: str, data: bytes) -> str:
        self.bucket.put_object(key, data)
        return key

    async def read(self, key: str) -> bytes:
        return self.bucket.get_object(key).read()

    async def delete(self, key: str) -> None:
        self.bucket.delete_object(key)

    async def exists(self, key: str) -> bool:
        return self.bucket.object_exists(key)

    def get_local_path(self, key: str) -> Path | None:
        return None

    def public_url(self, key: str) -> str | None:
        if not self.base_url:
            return None
        return f'{self.base_url}/{key}'

    def presigned_upload_url(self, key: str, expires: int = 900) -> str:
        return self.bucket.sign_url('PUT', key, expires)

    def presigned_download_url(self, key: str, expires: int = 900) -> str:
        return self.bucket.sign_url('GET', key, expires)


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == 'oss':
        return OSSStorageBackend()
    return LocalStorageBackend(settings.local_storage_path)
