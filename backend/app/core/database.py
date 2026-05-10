import sys

from sqlmodel import create_engine, Session, SQLModel

from app.core.config import settings
from app.exceptions.exception import FaceFeatException
from app.logging.logger import logging

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, echo=False)


def create_db_and_tables():
    try:
        logger.info("Creating DB tables via SQLModel.metadata.create_all (use Alembic in prod)")
        SQLModel.metadata.create_all(engine)
        logger.info("DB tables created successfully")
    except Exception as e:
        raise FaceFeatException(str(e), sys)


def get_session():
    """FastAPI dependency for DB session."""
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        raise FaceFeatException(str(e), sys)