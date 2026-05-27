from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import uuid4

from app.infrastructure.database.session import get_session
from app.infrastructure.database.models import UserModel, RoleModel, UserRoleModel
from app.interfaces.schemas.auth_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserMeResponse,
)
from app.application.use_cases.auth_service import AuthService
from app.infrastructure.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
auth_service = AuthService()


@router.post("/register", response_model=UserMeResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_session)):
    # Check if username exists
    existing_username = db.query(UserModel).filter(UserModel.username == payload.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    existing_email = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password and save user (is_active=False by default — awaiting admin approval)
    hashed = auth_service.hash_password(payload.password)
    user = UserModel(
        id=str(uuid4()),
        username=payload.username,
        email=payload.email,
        hashed_password=hashed,
        is_active=False  # Must be activated by admin before they can log in
    )
    db.add(user)
    db.flush()  # Get the user ID before committing

    # Always assign role "employee" to new registrations
    user_role = UserRoleModel(user_id=user.id, role_id="employee")
    db.add(user_role)

    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_session)):
    user = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn chưa được kích hoạt. Vui lòng liên hệ Admin."
        )

    token_payload = {"sub": user.id, "role": user.role_id}
    access_token = auth_service.create_access_token(data=token_payload)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user
