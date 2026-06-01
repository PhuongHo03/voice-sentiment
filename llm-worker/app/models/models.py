from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoleModel(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)


class UserRoleModel(Base):
    __tablename__ = "user_role"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )

    role: Mapped[RoleModel] = relationship(lazy="joined")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user_roles: Mapped[list[UserRoleModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def role_id(self) -> str:
        """Return the primary role id for this user (first role in user_role)."""
        if self.user_roles:
            return self.user_roles[0].role_id
        return "employee"

    @property
    def role(self) -> RoleModel | None:
        """Return the RoleModel object for this user's primary role."""
        if self.user_roles:
            return self.user_roles[0].role
        return None


class AnalysisJobModel(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str | None] = mapped_column(String(256))
    input_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    audio_object_key: Mapped[str | None] = mapped_column(String(512))
    submitted_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    result: Mapped["AnalysisResultModel | None"] = relationship(back_populates="job")
    owner: Mapped[UserModel | None] = relationship()


class AnalysisResultModel(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_jobs.id"), unique=True, nullable=False)
    transcript_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    summary_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(32), nullable=False)
    sentiment_reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    agent_score: Mapped[int | None] = mapped_column(nullable=True)
    agent_advice_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[AnalysisJobModel] = relationship(back_populates="result")
