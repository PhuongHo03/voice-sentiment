from fastapi import HTTPException, status

from app.models.models import UserModel
from app.repositories.admin_repository import AdminRepository
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository


class AdminService:
    def __init__(self, repository: AdminRepository, analysis_repository: SqlAlchemyAnalysisRepository):
        self.repository = repository
        self.analysis_repository = analysis_repository

    def get_employees(self) -> dict:
        employees = self.repository.list_employees()
        return {"employees": [self._build_employee_stats(emp) for emp in employees]}

    def get_employee_stats(self, employee_id: str) -> dict:
        self._require_employee(employee_id)
        return self.analysis_repository.get_analytics_stats(owner_id=employee_id)

    def get_employee_sessions(self, employee_id: str) -> dict:
        self._require_employee(employee_id)
        jobs = self.repository.list_employee_sessions(employee_id)
        sessions_list = []
        for job, result in jobs:
            sessions_list.append({
                "job_id": str(job.id),
                "name": job.name,
                "status": job.status,
                "input_type": job.input_type,
                "created_at": job.created_at,
                "sentiment": result.sentiment if result else None,
                "confidence": result.confidence if result else None,
                "agent_score": result.agent_score if result else None,
                "agent_advice": result.agent_advice_json if result else None,
                "summary": result.summary_json if result else None,
                "sentiment_reason": result.sentiment_reason if result else None,
                "transcript": result.transcript_json if result else None,
            })
        return {"sessions": sessions_list}

    def get_all_users(self) -> dict:
        result = []
        for user in self.repository.list_users():
            result.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role_id": user.role_id,
                "is_active": user.is_active,
                "created_at": user.created_at,
            })
        return {"users": result}

    def update_user_status(self, user_id: str, is_active: bool, current_admin: UserModel) -> dict:
        if user_id == current_admin.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự vô hiệu hóa tài khoản Admin đang đăng nhập.",
            )

        user = self.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user = self.repository.update_user_status(user, is_active)
        action = "kích hoạt" if is_active else "vô hiệu hóa"
        return {
            "message": f"Tài khoản '{user.username}' đã được {action} thành công.",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active,
                "role_id": user.role_id,
            },
        }

    def update_user_role(self, user_id: str, role_id: str, current_admin: UserModel) -> dict:
        role = self.repository.get_role(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vai trò '{role_id}' không tồn tại trong hệ thống.",
            )

        user = self.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự đổi vai trò của tài khoản Admin đang đăng nhập.",
            )

        user = self.repository.replace_user_role(user, role_id)
        return {
            "message": f"Đã cập nhật vai trò của '{user.username}' thành '{role.name}'.",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active,
                "role_id": user.role_id,
            },
        }

    def _build_employee_stats(self, emp: UserModel) -> dict:
        avg_score = self.repository.get_employee_average_score(emp.id)
        avg_score = round(float(avg_score), 1) if avg_score is not None else None

        sentiments = {"positive": 0, "neutral": 0, "negative": 0}
        for sent, count in self.repository.get_employee_sentiment_counts(emp.id):
            if sent and sent.lower() in sentiments:
                sentiments[sent.lower()] = count

        return {
            "id": emp.id,
            "username": emp.username,
            "email": emp.email,
            "total_jobs": self.repository.get_employee_job_count(emp.id),
            "average_score": avg_score,
            "sentiment_distribution": sentiments,
            "created_at": emp.created_at,
        }

    def _require_employee(self, employee_id: str) -> None:
        if not self.repository.has_employee_role(employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")
