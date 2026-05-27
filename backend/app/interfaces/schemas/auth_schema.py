from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserRoleResponse(BaseModel):
    id: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=6)
    # role_id is intentionally removed — all new registrations default to "employee"


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(...)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    id: str
    username: str
    email: str
    role_id: str
    role: UserRoleResponse | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    role_id: str


class AdminUserResponse(BaseModel):
    id: str
    username: str
    email: str
    role_id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
