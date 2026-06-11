from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import AnalysisJobModel, AnalysisResultModel


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def mark_processing(self, job_id: str) -> None:
        job = self.session.get(AnalysisJobModel, job_id)
        if job:
            job.status = "processing"
            job.started_at = func.now()
            job.last_heartbeat_at = func.now()
            job.completed_at = None
            job.failed_at = None
            job.error_message = None
            job.attempt_count = (job.attempt_count or 0) + 1
            self.session.commit()

    def touch_heartbeat(self, job_id: str) -> None:
        job = self.session.get(AnalysisJobModel, job_id)
        if job and job.status == "processing":
            job.last_heartbeat_at = func.now()
            self.session.commit()

    def save_completed(self, job_id: str, result: dict) -> None:
        job = self.session.get(AnalysisJobModel, job_id)
        if not job:
            return
        existing = self.session.query(AnalysisResultModel).filter_by(job_id=job_id).one_or_none()
        if not existing:
            existing = AnalysisResultModel(
                job_id=job_id,
                transcript_json=result["transcript"],
                summary_json=result["summary"],
                sentiment=result["sentiment"],
                sentiment_reason=result["sentiment_reason"],
                confidence=result["confidence"],
                agent_score=result.get("agent_score"),
                agent_advice_json=result.get("agent_advice"),
                detailed_summary_json=result.get("detailed_summary"),
                agent_score_breakdown_json=result.get("agent_score_breakdown"),
                quality_notes_json=result.get("quality_notes"),
                analysis_metadata_json=result.get("analysis_metadata"),
            )
            self.session.add(existing)
        else:
            existing.transcript_json = result["transcript"]
            existing.summary_json = result["summary"]
            existing.sentiment = result["sentiment"]
            existing.sentiment_reason = result["sentiment_reason"]
            existing.confidence = result["confidence"]
            existing.agent_score = result.get("agent_score")
            existing.agent_advice_json = result.get("agent_advice")
            existing.detailed_summary_json = result.get("detailed_summary")
            existing.agent_score_breakdown_json = result.get("agent_score_breakdown")
            existing.quality_notes_json = result.get("quality_notes")
            existing.analysis_metadata_json = result.get("analysis_metadata")
            
        job.status = "completed"
        job.error_message = None
        job.completed_at = func.now()
        job.failed_at = None
        job.last_heartbeat_at = func.now()
        self.session.commit()

    def save_failed(self, job_id: str, message: str) -> None:
        job = self.session.get(AnalysisJobModel, job_id)
        if job:
            job.status = "failed"
            job.error_message = message
            job.failed_at = func.now()
            job.last_heartbeat_at = func.now()
            self.session.commit()
