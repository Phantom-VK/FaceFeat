import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.database import create_db_and_tables
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

# ── CORS ────────────────────────────────────────────────────────
origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ────────────────────────────────────────────────────────────────

app.include_router(api_router)


@app.get("/")
def main():
    return {"status": "Running"}


@app.get("/health")
def health():
    return {"health": "ok"}