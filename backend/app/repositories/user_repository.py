from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.models import RoleModel, UserModel, UserRoleModel


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> UserModel | None:
        return self.session.query(UserModel).filter(UserModel.id == user_id).first()

    def get_by_username(self, username: str) -> UserModel | None:
        return self.session.query(UserModel).filter(UserModel.username == username).first()

    def get_by_email(self, email: str) -> UserModel | None:
        return self.session.query(UserModel).filter(UserModel.email == email).first()

    def get_role(self, role_id: str) -> RoleModel | None:
        return self.session.query(RoleModel).filter(RoleModel.id == role_id).first()

    def create_user(self, username: str, email: str, hashed_password: str, is_active: bool = False) -> UserModel:
        user = UserModel(
            id=str(uuid4()),
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def assign_role(self, user_id: str, role_id: str) -> UserRoleModel:
        user_role = UserRoleModel(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        return user_role

    def commit(self) -> None:
        self.session.commit()

    def refresh(self, user: UserModel) -> None:
        self.session.refresh(user)
