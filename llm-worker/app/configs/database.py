from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configs.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
