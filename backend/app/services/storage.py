"""Lưu trữ đối tượng (ảnh hiện trường, biên bản, mẫu biểu) trên MinIO/S3. Client `minio` là đồng bộ nên chạy trong thread."""
import asyncio
import io
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from ..config import settings


@lru_cache
def _client() -> Minio:
    return Minio(settings.minio_endpoint, access_key=settings.minio_root_user,
                 secret_key=settings.minio_root_password, secure=settings.minio_secure)


def _ensure_bucket() -> None:
    c = _client()
    if not c.bucket_exists(settings.minio_bucket):
        c.make_bucket(settings.minio_bucket)


async def ensure_bucket() -> None:
    await asyncio.to_thread(_ensure_bucket)


async def put(key: str, data: bytes, content_type: str) -> None:
    await asyncio.to_thread(lambda: _client().put_object(
        settings.minio_bucket, key, io.BytesIO(data), len(data), content_type=content_type))


async def get(key: str) -> bytes:
    def _get() -> bytes:
        r = _client().get_object(settings.minio_bucket, key)
        try:
            return r.read()
        finally:
            r.close()
            r.release_conn()
    try:
        return await asyncio.to_thread(_get)
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject"):
            raise FileNotFoundError(key)
        raise
