from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.configs.metrics import AUTH_EVENTS_TOTAL
from app.configs.session import get_session
from app.dtos.auth_schema import TokenResponse, UserLoginRequest, UserMeResponse, UserRegisterRequest
from app.middlewares.dependencies import get_current_user
from app.models.models import UserModel
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_service = AuthService()


@router.post("/register", response_model=UserMeResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_session)):
    try:
        result = auth_service.register(payload, UserRepository(db))
        AUTH_EVENTS_TOTAL.labels("register", "success").inc()
        return result
    except Exception:
        AUTH_EVENTS_TOTAL.labels("register", "failure").inc()
        raise


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_session)):
    try:
        result = auth_service.login(payload, UserRepository(db))
        AUTH_EVENTS_TOTAL.labels("login", "success").inc()
        return result
    except Exception:
        AUTH_EVENTS_TOTAL.labels("login", "failure").inc()
        raise


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user
