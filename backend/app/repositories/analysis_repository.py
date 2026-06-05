from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import AnalysisJobModel, AnalysisResultModel


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_audio_job(self, object_key: str, name: str | None = None, owner_id: str | None = None) -> AnalysisJobModel:
        job = AnalysisJobModel(input_type="audio", status="pending", audio_object_key=object_key, name=name, owner_id=owner_id)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def create_text_job(self, text: str, name: str | None = None, owner_id: str | None = None) -> AnalysisJobModel:
        job = AnalysisJobModel(input_type="text", status="pending", submitted_text=text, name=name, owner_id=owner_id)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: str) -> AnalysisJobModel | None:
        return self.session.get(AnalysisJobModel, job_id)

    def get_result(self, job_id: str) -> AnalysisResultModel | None:
        return self.session.query(AnalysisResultModel).filter_by(job_id=job_id).one_or_none()

    def list_jobs(self, limit: int = 20, offset: int = 0, owner_id: str | None = None) -> list[tuple[AnalysisJobModel, AnalysisResultModel | None]]:
        # Perform a left outer join to get jobs with their results
        query = (
            self.session.query(AnalysisJobModel, AnalysisResultModel)
            .outerjoin(AnalysisResultModel, AnalysisJobModel.id == AnalysisResultModel.job_id)
        )
        if owner_id:
            query = query.filter(AnalysisJobModel.owner_id == owner_id)
            
        query = query.order_by(AnalysisJobModel.created_at.desc()).offset(offset).limit(limit)
        return query.all()

    def count_jobs(self, owner_id: str | None = None) -> int:
        query = self.session.query(AnalysisJobModel)
        if owner_id:
            query = query.filter(AnalysisJobModel.owner_id == owner_id)
        return query.count()

    def update_job_name(self, job_id: str, name: str) -> AnalysisJobModel | None:
        job = self.get_job(job_id)
        if job:
            job.name = name
            self.session.commit()
            self.session.refresh(job)
        return job

    def delete_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job:
            self.session.delete(job)
            self.session.commit()
            return True
        return False

    def has_active_job_for_key(self, object_key: str) -> bool:
        """Return True if any pending/processing job is currently using this MinIO object key."""
        count = (
            self.session.query(AnalysisJobModel)
            .filter(
                AnalysisJobModel.audio_object_key == object_key,
                AnalysisJobModel.status.in_(["pending", "processing"]),
            )
            .count()
        )
        return count > 0

    def has_job_referencing_key(self, object_key: str) -> bool:
        """Return True if any job is currently referencing this MinIO object key."""
        count = (
            self.session.query(AnalysisJobModel)
            .filter(AnalysisJobModel.audio_object_key == object_key)
            .count()
        )
        return count > 0

    def get_analytics_stats(self, owner_id: str | None = None) -> dict:
        # Query total jobs
        total_query = self.session.query(AnalysisResultModel).join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)
        if owner_id:
            total_query = total_query.filter(AnalysisJobModel.owner_id == owner_id)
        total_jobs = total_query.count()
        
        # Sentiment distribution
        sent_query = self.session.query(
            AnalysisResultModel.sentiment,
            func.count(AnalysisResultModel.id)
        ).join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)
        if owner_id:
            sent_query = sent_query.filter(AnalysisJobModel.owner_id == owner_id)
        sentiments = sent_query.group_by(AnalysisResultModel.sentiment).all()
        
        sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
        for s_type, count in sentiments:
            if s_type:
                sentiment_dist[s_type.lower()] = count

        # Average confidence
        conf_query = self.session.query(func.avg(AnalysisResultModel.confidence)).join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)
        if owner_id:
            conf_query = conf_query.filter(AnalysisJobModel.owner_id == owner_id)
        avg_conf = conf_query.scalar() or 0.0

        # Average agent score
        score_query = self.session.query(func.avg(AnalysisResultModel.agent_score)).join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)
        if owner_id:
            score_query = score_query.filter(AnalysisJobModel.owner_id == owner_id)
        avg_score = score_query.scalar() or 0.0

        # Weekly trends: count jobs created on each of the last 7 days
        today = datetime.utcnow().date()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        
        trends = {day.strftime("%Y-%m-%d"): 0 for day in days}
        
        start_date = datetime.combine(days[0], datetime.min.time())
        trend_query = self.session.query(
            func.date(AnalysisJobModel.created_at).label("day"),
            func.count(AnalysisJobModel.id)
        ).filter(AnalysisJobModel.created_at >= start_date)
        if owner_id:
            trend_query = trend_query.filter(AnalysisJobModel.owner_id == owner_id)
        daily_counts = trend_query.group_by(func.date(AnalysisJobModel.created_at)).all()
         
        for day, count in daily_counts:
            if day:
                day_str = day.strftime("%Y-%m-%d") if not isinstance(day, str) else day[:10]
                if day_str in trends:
                    trends[day_str] = count

        weekly_trends_list = [{"date": k, "count": v} for k, v in trends.items()]

        return {
            "total_jobs": total_jobs,
            "sentiment_distribution": sentiment_dist,
            "average_confidence": round(float(avg_conf), 2),
            "average_agent_score": round(float(avg_score), 1),
            "weekly_trends": weekly_trends_list
        }
