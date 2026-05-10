from sqlmodel import create_engine, Session, SQLModel

from app.core.config import settings
from app.logging.logger import logging

engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    logging.info("Initializing database...")
    SQLModel.metadata.create_all(engine)
    logging.info("Database initialized.")

def get_session():
    logging.info("Initializing session...")
    with Session(engine) as session:
        yield session