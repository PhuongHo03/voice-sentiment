import logging

from fastapi import HTTPException

from app.configs.cache import RedisJobCache
from app.configs.queue import RabbitMqJobPublisher
from app.configs.storage import MinioAudioStorage
from app.models.models import UserModel
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(
        self,
        repository: SqlAlchemyAnalysisRepository,
        cache: RedisJobCache | None = None,
        publisher: RabbitMqJobPublisher | None = None,
        storage: MinioAudioStorage | None = None,
    ):
        self.repository = repository
        self.cache = cache
        self.publisher = publisher or RabbitMqJobPublisher()
        self.storage = storage

    def submit_audio(self, filename: str, content: bytes, content_type: str, owner_id: str | None = None) -> dict:
        object_key = self._storage().save(filename, content, content_type, owner_id=owner_id)
        job = self.repository.create_audio_job(object_key, name=filename, owner_id=owner_id)
        self.publisher.publish({"job_id": str(job.id), "input_type": "audio", "audio_object_key": object_key, "owner_id": owner_id}, owner_id=owner_id)
        self._cache_pending(str(job.id), owner_id=owner_id)
        return {"job_id": str(job.id), "status": job.status}

    def submit_text(self, text: str, owner_id: str | None = None) -> dict:
        name = text[:60] + "..." if len(text) > 60 else text
        job = self.repository.create_text_job(text, name=name, owner_id=owner_id)
        self.publisher.publish({"job_id": str(job.id), "input_type": "text", "text": text, "owner_id": owner_id}, owner_id=owner_id)
        self._cache_pending(str(job.id), owner_id=owner_id)
        return {"job_id": str(job.id), "status": job.status}

    def submit_audio_from_key(self, object_key: str, name: str | None, owner_id: str) -> dict:
        expected_prefix = f"uploads/{owner_id}/"
        if not object_key.startswith(expected_prefix):
            raise HTTPException(status_code=403, detail="You do not have permission to use this file")

        job = self.repository.create_audio_job(object_key, name=name or object_key.split("/")[-1], owner_id=owner_id)
        self.publisher.publish(
            {"job_id": str(job.id), "input_type": "audio", "audio_object_key": object_key, "owner_id": owner_id},
            owner_id=owner_id,
        )
        self._cache_pending(str(job.id), owner_id=owner_id)
        return {"job_id": str(job.id), "status": job.status}

    def list_sessions(self, limit: int, offset: int, owner_id: str) -> dict:
        db_sessions = self.repository.list_jobs(limit=limit, offset=offset, owner_id=owner_id)
        total = self.repository.count_jobs(owner_id=owner_id)

        sessions_list = []
        for job, result in db_sessions:
            sessions_list.append({
                "job_id": str(job.id),
                "name": job.name,
                "status": job.status,
                "input_type": job.input_type,
                "created_at": job.created_at,
                "sentiment": result.sentiment if result else None,
                "confidence": result.confidence if result else None,
            })

        return {"sessions": sessions_list, "total": total, "offset": offset, "limit": limit}

    def get_stats(self, owner_id: str) -> dict:
        try:
            cached_stats = self._cache().get_stats(owner_id)
            if cached_stats is not None:
                return cached_stats
        except Exception as e:
            logger.warning(f"Failed to read stats cache for user {owner_id}: {e}")

        stats = self.repository.get_analytics_stats(owner_id=owner_id)

        try:
            self._cache().set_stats(owner_id, stats)
        except Exception as e:
            logger.warning(f"Failed to write stats cache for user {owner_id}: {e}")

        return stats

    def get_analysis(self, job_id: str, current_user: UserModel) -> dict:
        job = self._get_authorized_job(job_id, current_user)

        cached = self._cache().get(job_id, owner_id=current_user.id)
        if cached:
            cached["name"] = job.name
            cached["input_type"] = job.input_type
            cached["audio_object_key"] = job.audio_object_key
            return cached

        result = self.repository.get_result(job_id)
        return self._job_payload(job, result)

    def rename_session(self, job_id: str, name: str, current_user: UserModel) -> dict:
        self._get_authorized_job(job_id, current_user)
        job = self.repository.update_job_name(job_id, name)
        result = self.repository.get_result(job_id)
        return self._job_payload(job, result)

    def delete_session(self, job_id: str, current_user: UserModel) -> dict:
        self._get_authorized_job(job_id, current_user)
        self.repository.delete_job(job_id)

        try:
            self._cache().delete(job_id, owner_id=current_user.id)
            self._cache().delete_stats(current_user.id)
        except Exception:
            pass

        return {"message": "Session deleted successfully"}

    def _get_authorized_job(self, job_id: str, current_user: UserModel):
        job = self.repository.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Analysis job not found")
        if job.owner_id and job.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to access this session")
        return job

    def _cache_pending(self, job_id: str, owner_id: str | None = None) -> None:
        try:
            self._cache().set_status(job_id, {"job_id": job_id, "status": "pending"}, owner_id=owner_id)
        except Exception as e:
            logger.warning(f"Failed to cache pending job {job_id}: {e}")

    def _cache(self) -> RedisJobCache:
        if self.cache is None:
            self.cache = RedisJobCache()
        return self.cache

    def _storage(self) -> MinioAudioStorage:
        if self.storage is None:
            self.storage = MinioAudioStorage()
        return self.storage

    def _job_payload(self, job, result) -> dict:
        result_payload = None
        if result:
            result_payload = {
                "transcript": result.transcript_json,
                "summary": result.summary_json,
                "sentiment": result.sentiment,
                "sentiment_reason": result.sentiment_reason,
                "confidence": result.confidence,
                "agent_score": result.agent_score,
                "agent_advice": result.agent_advice_json,
                "detailed_summary": result.detailed_summary_json,
                "agent_score_breakdown": result.agent_score_breakdown_json,
                "quality_notes": result.quality_notes_json,
                "analysis_metadata": result.analysis_metadata_json,
            }
        return {
            "job_id": str(job.id),
            "name": job.name,
            "status": job.status,
            "input_type": job.input_type,
            "audio_object_key": job.audio_object_key,
            "result": result_payload,
            "error_message": job.error_message,
        }


class SubmitAudioAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, storage: MinioAudioStorage, publisher: RabbitMqJobPublisher):
        self.service = AnalysisService(repository, publisher=publisher, storage=storage)

    def execute(self, filename: str, content: bytes, content_type: str, owner_id: str | None = None) -> dict:
        return self.service.submit_audio(filename, content, content_type, owner_id=owner_id)


class SubmitTextAnalysis:
    def __init__(self, repository: SqlAlchemyAnalysisRepository, publisher: RabbitMqJobPublisher):
        self.service = AnalysisService(repository, publisher=publisher)

    def execute(self, text: str, owner_id: str | None = None) -> dict:
        return self.service.submit_text(text, owner_id=owner_id)
