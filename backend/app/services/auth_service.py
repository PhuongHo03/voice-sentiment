from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.configs.config import settings
from app.dtos.auth_schema import UserLoginRequest, UserRegisterRequest
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self):
        self.secret_key = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_expires_minutes

    def hash_password(self, password: str) -> str:
        # Generate salt and hash the password
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None

    def register(self, payload: UserRegisterRequest, users: UserRepository):
        existing_username = users.get_by_username(payload.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        existing_email = users.get_by_email(payload.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed = self.hash_password(payload.password)
        user = users.create_user(payload.username, payload.email, hashed, is_active=False)
        users.assign_role(user.id, "employee")
        users.commit()
        users.refresh(user)
        return user

    def login(self, payload: UserLoginRequest, users: UserRepository) -> dict:
        user = users.get_by_email(payload.email)
        if not user or not self.verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn chưa được kích hoạt. Vui lòng liên hệ Admin.",
            )

        token_payload = {"sub": user.id, "role": user.role_id}
        access_token = self.create_access_token(data=token_payload)
        return {"access_token": access_token, "token_type": "bearer"}
