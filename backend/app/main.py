from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keeping this function call for local dev, might remove and let alembic handle the database
    create_db_and_tables()
    yield

app = FastAPI(title="Face ROI API", lifespan=lifespan)

@app.get("/")
def main():
    return {"status": "Running"}

@app.get("/health")
def health():
    return {"health": "ok"}
