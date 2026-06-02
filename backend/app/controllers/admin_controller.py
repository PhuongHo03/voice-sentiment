from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.configs.session import get_session
from app.dtos.auth_schema import UpdateUserRoleRequest, UpdateUserStatusRequest
from app.middlewares.dependencies import require_admin
from app.models.models import UserModel
from app.repositories.admin_repository import AdminRepository
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_service(session: Session) -> AdminService:
    return AdminService(AdminRepository(session), SqlAlchemyAnalysisRepository(session))


@router.get("/employees")
def get_employees(db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """List all employee accounts with performance stats."""
    return _admin_service(db).get_employees()


@router.get("/employees/{employee_id}/stats")
def get_employee_stats(employee_id: str, db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """Get detailed analytics stats for a specific employee."""
    return _admin_service(db).get_employee_stats(employee_id)


@router.get("/employees/{employee_id}/sessions")
def get_employee_sessions(employee_id: str, db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """List all analysis sessions for a specific employee."""
    return _admin_service(db).get_employee_sessions(employee_id)


@router.get("/users")
def get_all_users(db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """List all user accounts with their roles and activation status."""
    return _admin_service(db).get_all_users()


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    db: Session = Depends(get_session),
    current_admin: UserModel = Depends(require_admin),
):
    """Activate or deactivate a user account."""
    return _admin_service(db).update_user_status(user_id, payload.is_active, current_admin)


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    payload: UpdateUserRoleRequest,
    db: Session = Depends(get_session),
    current_admin: UserModel = Depends(require_admin),
):
    """Change a user's role (admin ↔ employee)."""
    return _admin_service(db).update_user_role(user_id, payload.role_id, current_admin)


@router.get("/metrics")
def get_system_metrics(db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """Get system observability metrics scraped by Prometheus (secured with admin auth)."""
    return _admin_service(db).get_system_metrics()
