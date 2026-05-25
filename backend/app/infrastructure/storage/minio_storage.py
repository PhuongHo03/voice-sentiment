from io import BytesIO
from uuid import uuid4

from minio import Minio

from app.core.config import settings


class MinioAudioStorage:
    def __init__(self) -> None:
        self.client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)
        if not self.client.bucket_exists(settings.minio_bucket):
            self.client.make_bucket(settings.minio_bucket)

    def save(self, filename: str, content: bytes, content_type: str) -> str:
        suffix = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        object_key = f"uploads/{uuid4()}.{suffix}"
        self.client.put_object(settings.minio_bucket, object_key, BytesIO(content), length=len(content), content_type=content_type)
        return object_key
