from datetime import timedelta
from typing import Any
import logging

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
from minio import Minio

from app.configs.config import settings
from app.configs.storage import MinioAudioStorage
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, repository: SqlAlchemyAnalysisRepository | None = None):
        self.repository = repository

    def upload(self, filename: str, content: bytes, content_type: str, owner_id: str) -> dict[str, Any]:
        storage = MinioAudioStorage()
        object_key = storage.save(filename, content, content_type, owner_id=owner_id)
        return {
            "object_key": object_key,
            "name": object_key.split("/")[-1],
            "original_name": filename,
            "size": len(content),
        }

    def list_files(self, owner_id: str) -> dict[str, Any]:
        client = self._get_minio_client()
        prefix = f"uploads/{owner_id}/"

        try:
            objects = client.list_objects(settings.minio_bucket, prefix=prefix, recursive=True)
            files = []
            for obj in objects:
                files.append(
                    {
                        "object_key": obj.object_name,
                        "name": obj.object_name.split("/")[-1],
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                        "etag": obj.etag,
                    }
                )
            files.sort(key=lambda f: f["last_modified"] or "", reverse=True)
            return {"files": files, "total": len(files)}
        except Exception as e:
            logger.error(f"Failed to list MinIO files for user {owner_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to list files from storage")

    def get_presigned_url(self, object_key: str, owner_id: str) -> dict[str, str]:
        self._require_owner_prefix(object_key, owner_id, "access this file")
        client = self._get_minio_client()
        try:
            url = client.presigned_get_object(
                settings.minio_bucket,
                object_key,
                expires=timedelta(hours=1),
            )
            if "minio:9000" in url:
                url = url.replace("minio:9000", "localhost:9000")
            return {"url": url}
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {object_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate file URL")

    def stream(self, object_key: str, request: Request, token: str | None) -> StreamingResponse:
        if not token:
            raise HTTPException(status_code=401, detail="Authentication token required")

        payload = AuthService().decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token subject")

        self._require_owner_prefix(object_key, user_id, "access this file")
        client = self._get_minio_client()

        try:
            stat = client.stat_object(settings.minio_bucket, object_key)
            file_size = stat.size
        except Exception as e:
            logger.error(f"File not found in MinIO: {object_key} - {e}")
            raise HTTPException(status_code=404, detail="File not found")

        media_type = self._media_type(object_key)
        status_code = 200
        headers = {
            "Content-Disposition": f'inline; filename="{object_key.split("/")[-1]}"',
            "Accept-Ranges": "bytes",
        }
        offset = 0
        length = file_size

        range_header = request.headers.get("Range")
        if range_header:
            try:
                range_header = range_header.strip()
                if range_header.startswith("bytes="):
                    range_val = range_header.split("=")[1]
                    ranges = range_val.split("-")
                    start_byte = int(ranges[0]) if ranges[0] else 0
                    end_byte = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1

                    if start_byte >= file_size:
                        raise HTTPException(
                            status_code=416,
                            detail=f"Requested range not satisfiable: {start_byte} >= {file_size}",
                        )

                    if end_byte >= file_size:
                        end_byte = file_size - 1

                    offset = start_byte
                    length = end_byte - start_byte + 1
                    status_code = 206
                    headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
            except (ValueError, IndexError):
                status_code = 200
                offset = 0
                length = file_size

        headers["Content-Length"] = str(length)

        try:
            response = client.get_object(settings.minio_bucket, object_key, offset=offset, length=length)

            def chunk_generator():
                try:
                    for chunk in response.stream(32 * 1024):
                        yield chunk
                finally:
                    response.close()
                    response.release_conn()

            return StreamingResponse(chunk_generator(), status_code=status_code, media_type=media_type, headers=headers)
        except Exception as e:
            logger.error(f"Failed to stream file {object_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to stream file from storage")

    def delete(self, object_key: str, owner_id: str) -> dict[str, str]:
        self._require_owner_prefix(object_key, owner_id, "delete this file")
        if self.repository and self.repository.has_job_referencing_key(object_key):
            if self.repository.has_active_job_for_key(object_key):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Không thể xóa file: đang có job phân tích (pending/processing) sử dụng file này. "
                        "Vui lòng chờ job hoàn thành hoặc thất bại trước khi xóa."
                    ),
                )
            else:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Không thể xóa file: file này đang được liên kết với một phiên phân tích (session). "
                        "Vui lòng xóa phiên phân tích trước khi xóa file."
                    ),
                )

        client = self._get_minio_client()
        try:
            client.remove_object(settings.minio_bucket, object_key)
            return {"message": "File deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete file {object_key}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete file from storage")

    def _get_minio_client(self) -> Minio:
        return Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def _require_owner_prefix(self, object_key: str, owner_id: str, action: str) -> None:
        expected_prefix = f"uploads/{owner_id}/"
        if not object_key.startswith(expected_prefix):
            raise HTTPException(status_code=403, detail=f"You do not have permission to {action}")

    def _media_type(self, object_key: str) -> str:
        if object_key.endswith(".mp3"):
            return "audio/mpeg"
        if object_key.endswith(".wav"):
            return "audio/wav"
        if object_key.endswith(".webm"):
            return "audio/webm"
        if object_key.endswith(".mp4"):
            return "video/mp4"
        return "application/octet-stream"
