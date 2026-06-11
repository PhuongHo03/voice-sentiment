import logging
from datetime import datetime, timezone

from fastapi import HTTPException

from app.configs.cache import RedisJobCache
from app.configs.queue import RabbitMqJobPublisher
from app.configs.storage import MinioAudioStorage
from app.models.models import UserModel
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository

logger = logging.getLogger(__name__)
JOB_STUCK_TIMEOUT_SECONDS = 30 * 60
JOB_RECOVERY_INTERVAL_SECONDS = 5 * 60
MAX_JOB_ATTEMPTS = 3


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

    def retry_session(self, job_id: str, current_user: UserModel) -> dict:
        job = self._get_authorized_job(job_id, current_user)
        result = self.repository.get_result(job_id)
        if result:
            raise HTTPException(status_code=400, detail="Completed jobs with results cannot be retried")
        if job.status == "processing" and not self._is_stuck(job):
            raise HTTPException(status_code=409, detail="Job is still actively processing")
        if job.status not in {"failed", "processing"}:
            raise HTTPException(status_code=400, detail="This job cannot be retried")
        if (job.attempt_count or 0) >= MAX_JOB_ATTEMPTS:
            raise HTTPException(status_code=400, detail="Maximum retry attempts reached")

        retried = self._requeue_job(job)
        return self._job_payload(retried, None)

    def recover_stuck_jobs(self, limit: int = 50) -> int:
        jobs = self.repository.get_stuck_processing_jobs(
            stale_after_seconds=JOB_STUCK_TIMEOUT_SECONDS,
            max_attempts=MAX_JOB_ATTEMPTS,
            limit=limit,
        )
        recovered = 0
        for job in jobs:
            try:
                self._requeue_job(job)
                recovered += 1
            except Exception as exc:
                logger.error(f"Failed to requeue stuck job {job.id}: {exc}")
        if recovered:
            logger.warning(f"Recovered {recovered} stuck analysis job(s).")
        return recovered

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

    def _requeue_job(self, job) -> object:
        payload = self._job_message(job)
        retried = self.repository.reset_job_for_retry(str(job.id))
        if retried is None:
            raise HTTPException(status_code=404, detail="Analysis job not found")
        self.publisher.publish(payload, owner_id=retried.owner_id)
        self._cache_pending(str(retried.id), owner_id=retried.owner_id)
        if retried.owner_id:
            try:
                self._cache().delete_stats(retried.owner_id)
            except Exception:
                pass
        return retried

    def _job_message(self, job) -> dict:
        payload = {"job_id": str(job.id), "input_type": job.input_type, "owner_id": job.owner_id}
        if job.input_type == "audio":
            if not job.audio_object_key:
                raise HTTPException(status_code=400, detail="Audio job is missing object key")
            payload["audio_object_key"] = job.audio_object_key
        elif job.input_type == "text":
            if not job.submitted_text:
                raise HTTPException(status_code=400, detail="Text job is missing submitted text")
            payload["text"] = job.submitted_text
        else:
            raise HTTPException(status_code=400, detail="Unsupported job input type")
        return payload

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

    def _is_stuck(self, job) -> bool:
        marker = job.last_heartbeat_at or job.started_at or job.updated_at
        if marker is None:
            return True
        if marker.tzinfo is None:
            marker = marker.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - marker).total_seconds()
        return age_seconds >= JOB_STUCK_TIMEOUT_SECONDS


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
