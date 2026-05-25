from sqlalchemy.orm import Session

from app.infrastructure.database.models import AnalysisJobModel, AnalysisResultModel


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_audio_job(self, object_key: str) -> AnalysisJobModel:
        job = AnalysisJobModel(input_type="audio", status="pending", audio_object_key=object_key)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def create_text_job(self, text: str) -> AnalysisJobModel:
        job = AnalysisJobModel(input_type="text", status="pending", submitted_text=text)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: str) -> AnalysisJobModel | None:
        return self.session.get(AnalysisJobModel, job_id)

    def get_result(self, job_id: str) -> AnalysisResultModel | None:
        return self.session.query(AnalysisResultModel).filter_by(job_id=job_id).one_or_none()
