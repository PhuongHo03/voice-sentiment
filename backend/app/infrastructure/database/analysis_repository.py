from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.database.models import AnalysisJobModel, AnalysisResultModel


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_audio_job(self, object_key: str, name: str | None = None) -> AnalysisJobModel:
        job = AnalysisJobModel(input_type="audio", status="pending", audio_object_key=object_key, name=name)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def create_text_job(self, text: str, name: str | None = None) -> AnalysisJobModel:
        job = AnalysisJobModel(input_type="text", status="pending", submitted_text=text, name=name)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: str) -> AnalysisJobModel | None:
        return self.session.get(AnalysisJobModel, job_id)

    def get_result(self, job_id: str) -> AnalysisResultModel | None:
        return self.session.query(AnalysisResultModel).filter_by(job_id=job_id).one_or_none()

    def list_jobs(self, limit: int = 20, offset: int = 0) -> list[tuple[AnalysisJobModel, AnalysisResultModel | None]]:
        # Perform a left outer join to get jobs with their results
        query = (
            self.session.query(AnalysisJobModel, AnalysisResultModel)
            .outerjoin(AnalysisResultModel, AnalysisJobModel.id == AnalysisResultModel.job_id)
            .order_by(AnalysisJobModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return query.all()

    def count_jobs(self) -> int:
        return self.session.query(AnalysisJobModel).count()

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

    def get_analytics_stats(self) -> dict:
        # Total jobs with results
        total_jobs = self.session.query(AnalysisResultModel).count()
        
        # Sentiment distribution
        sentiments = self.session.query(
            AnalysisResultModel.sentiment,
            func.count(AnalysisResultModel.id)
        ).group_by(AnalysisResultModel.sentiment).all()
        
        sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
        for s_type, count in sentiments:
            if s_type:
                sentiment_dist[s_type.lower()] = count

        # Average confidence
        avg_conf = self.session.query(func.avg(AnalysisResultModel.confidence)).scalar() or 0.0

        # Average agent score
        avg_score = self.session.query(func.avg(AnalysisResultModel.agent_score)).scalar() or 0.0

        # Weekly trends: count jobs created on each of the last 7 days
        today = datetime.utcnow().date()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        
        trends = {day.strftime("%Y-%m-%d"): 0 for day in days}
        
        start_date = datetime.combine(days[0], datetime.min.time())
        daily_counts = self.session.query(
            func.date(AnalysisJobModel.created_at).label("day"),
            func.count(AnalysisJobModel.id)
        ).filter(AnalysisJobModel.created_at >= start_date)\
         .group_by(func.date(AnalysisJobModel.created_at)).all()
         
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
