import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import create_db_and_tables
from app.api.routes.video import router as video_router
from app.exceptions.exception import FaceFeatException
from app.logging.logger import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_db_and_tables()
        logger.info("App startup complete. Registered routes:")
        for route in app.routes:
            logger.info(f"  {route.path}")
    except Exception as e:
        raise FaceFeatException(str(e), sys)
    yield


app = FastAPI(title="Face ROI API", lifespan=lifespan)

app.include_router(video_router)


@app.get("/")
def main():
    return {"status": "Running"}


@app.get("/health")
def health():
    return {"health": "ok"}