from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.configs.config import settings
from app.models.models import Base

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    with SessionLocal() as session:
        yield session
