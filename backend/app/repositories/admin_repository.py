from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import AnalysisJobModel, AnalysisResultModel, RoleModel, UserModel, UserRoleModel


class AdminRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_employees(self) -> list[UserModel]:
        employee_ids = self.session.query(UserRoleModel.user_id).filter(UserRoleModel.role_id == "employee").subquery()
        return self.session.query(UserModel).filter(UserModel.id.in_(employee_ids)).all()

    def has_employee_role(self, user_id: str) -> bool:
        return self.session.query(UserRoleModel).filter(
            UserRoleModel.user_id == user_id,
            UserRoleModel.role_id == "employee",
        ).first() is not None

    def get_employee_job_count(self, employee_id: str) -> int:
        return self.session.query(func.count(AnalysisJobModel.id)).filter(AnalysisJobModel.owner_id == employee_id).scalar() or 0

    def get_employee_average_score(self, employee_id: str) -> float | None:
        return self.session.query(func.avg(AnalysisResultModel.agent_score))\
            .join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)\
            .filter(AnalysisJobModel.owner_id == employee_id).scalar()

    def get_employee_sentiment_counts(self, employee_id: str) -> list[tuple[str, int]]:
        return self.session.query(
            AnalysisResultModel.sentiment,
            func.count(AnalysisResultModel.id),
        ).join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)\
         .filter(AnalysisJobModel.owner_id == employee_id)\
         .group_by(AnalysisResultModel.sentiment).all()

    def list_employee_sessions(self, employee_id: str) -> list[tuple[AnalysisJobModel, AnalysisResultModel | None]]:
        return self.session.query(AnalysisJobModel, AnalysisResultModel)\
            .outerjoin(AnalysisResultModel, AnalysisJobModel.id == AnalysisResultModel.job_id)\
            .filter(AnalysisJobModel.owner_id == employee_id)\
            .order_by(AnalysisJobModel.created_at.desc()).all()

    def list_users(self) -> list[UserModel]:
        return self.session.query(UserModel).order_by(UserModel.created_at.desc()).all()

    def get_user(self, user_id: str) -> UserModel | None:
        return self.session.query(UserModel).filter(UserModel.id == user_id).first()

    def get_role(self, role_id: str) -> RoleModel | None:
        return self.session.query(RoleModel).filter(RoleModel.id == role_id).first()

    def update_user_status(self, user: UserModel, is_active: bool) -> UserModel:
        user.is_active = is_active
        self.session.commit()
        self.session.refresh(user)
        return user

    def replace_user_role(self, user: UserModel, role_id: str) -> UserModel:
        self.session.query(UserRoleModel).filter(UserRoleModel.user_id == user.id).delete()
        self.session.add(UserRoleModel(user_id=user.id, role_id=role_id))
        self.session.commit()
        self.session.refresh(user)
        return user
