from minio import Minio

from app.core.config import settings


class MinioAudioStorage:
    def __init__(self) -> None:
        self.client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)

    def read(self, object_key: str) -> bytes:
        response = self.client.get_object(settings.minio_bucket, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
