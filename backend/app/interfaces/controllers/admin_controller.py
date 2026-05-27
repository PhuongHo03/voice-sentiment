from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import UserModel, UserRoleModel, AnalysisJobModel, AnalysisResultModel, RoleModel
from app.infrastructure.dependencies import require_admin
from app.infrastructure.database.analysis_repository import SqlAlchemyAnalysisRepository
from app.interfaces.schemas.auth_schema import UpdateUserStatusRequest, UpdateUserRoleRequest, AdminUserResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ──────────────────────────────────────────────────────────────────────────────
# Helper: build employee statistics for a single user
# ──────────────────────────────────────────────────────────────────────────────
def _build_employee_stats(db: Session, emp: UserModel) -> dict:
    total_jobs = db.query(func.count(AnalysisJobModel.id))\
        .filter(AnalysisJobModel.owner_id == emp.id).scalar() or 0

    avg_score = db.query(func.avg(AnalysisResultModel.agent_score))\
        .join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)\
        .filter(AnalysisJobModel.owner_id == emp.id).scalar()
    avg_score = round(float(avg_score), 1) if avg_score is not None else None

    sentiment_counts = db.query(
        AnalysisResultModel.sentiment,
        func.count(AnalysisResultModel.id)
    ).join(AnalysisJobModel, AnalysisJobModel.id == AnalysisResultModel.job_id)\
     .filter(AnalysisJobModel.owner_id == emp.id)\
     .group_by(AnalysisResultModel.sentiment).all()

    sentiments = {"positive": 0, "neutral": 0, "negative": 0}
    for sent, count in sentiment_counts:
        if sent and sent.lower() in sentiments:
            sentiments[sent.lower()] = count

    return {
        "id": emp.id,
        "username": emp.username,
        "email": emp.email,
        "total_jobs": total_jobs,
        "average_score": avg_score,
        "sentiment_distribution": sentiments,
        "created_at": emp.created_at,
    }


# ──────────────────────────────────────────────────────────────────────────────
# EMPLOYEE PERFORMANCE ENDPOINTS (existing)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/employees")
def get_employees(db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """List all employee accounts with performance stats."""
    employee_ids = db.query(UserRoleModel.user_id).filter(UserRoleModel.role_id == "employee").subquery()
    employees = db.query(UserModel).filter(UserModel.id.in_(employee_ids)).all()

    results = [_build_employee_stats(db, emp) for emp in employees]
    return {"employees": results}


@router.get("/employees/{employee_id}/stats")
def get_employee_stats(employee_id: str, db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """Get detailed analytics stats for a specific employee."""
    emp_role = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == employee_id,
        UserRoleModel.role_id == "employee"
    ).first()
    if not emp_role:
        raise HTTPException(status_code=404, detail="Employee not found")

    repository = SqlAlchemyAnalysisRepository(db)
    return repository.get_analytics_stats(owner_id=employee_id)


@router.get("/employees/{employee_id}/sessions")
def get_employee_sessions(employee_id: str, db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """List all analysis sessions for a specific employee."""
    emp_role = db.query(UserRoleModel).filter(
        UserRoleModel.user_id == employee_id,
        UserRoleModel.role_id == "employee"
    ).first()
    if not emp_role:
        raise HTTPException(status_code=404, detail="Employee not found")

    jobs = db.query(AnalysisJobModel, AnalysisResultModel)\
        .outerjoin(AnalysisResultModel, AnalysisJobModel.id == AnalysisResultModel.job_id)\
        .filter(AnalysisJobModel.owner_id == employee_id)\
        .order_by(AnalysisJobModel.created_at.desc()).all()

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


# ──────────────────────────────────────────────────────────────────────────────
# ACCOUNT MANAGEMENT ENDPOINTS (new)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/users")
def get_all_users(db: Session = Depends(get_session), current_admin: UserModel = Depends(require_admin)):
    """List all user accounts with their roles and activation status."""
    users = db.query(UserModel).order_by(UserModel.created_at.desc()).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role_id": u.role_id,
            "is_active": u.is_active,
            "created_at": u.created_at,
        })
    return {"users": result}


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    db: Session = Depends(get_session),
    current_admin: UserModel = Depends(require_admin)
):
    """Activate or deactivate a user account."""
    # Prevent admin from deactivating themselves
    if user_id == current_admin.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự vô hiệu hóa tài khoản Admin đang đăng nhập."
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    action = "kích hoạt" if payload.is_active else "vô hiệu hóa"
    return {
        "message": f"Tài khoản '{user.username}' đã được {action} thành công.",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_active": user.is_active,
            "role_id": user.role_id,
        }
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    payload: UpdateUserRoleRequest,
    db: Session = Depends(get_session),
    current_admin: UserModel = Depends(require_admin)
):
    """Change a user's role (admin ↔ employee)."""
    # Validate role exists
    role = db.query(RoleModel).filter(RoleModel.id == payload.role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vai trò '{payload.role_id}' không tồn tại trong hệ thống."
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from changing own role (to avoid lockout)
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự đổi vai trò của tài khoản Admin đang đăng nhập."
        )

    # Delete existing user_role entries and insert new one
    db.query(UserRoleModel).filter(UserRoleModel.user_id == user_id).delete()
    new_role = UserRoleModel(user_id=user_id, role_id=payload.role_id)
    db.add(new_role)
    db.commit()
    db.refresh(user)

    return {
        "message": f"Đã cập nhật vai trò của '{user.username}' thành '{role.name}'.",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_active": user.is_active,
            "role_id": user.role_id,
        }
    }
