from pydantic_settings import BaseSettings
from pathlib import Path
import os
import dotenv

dotenv.load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    APP_ENV: str = "development"

    UPLOAD_DIR: Path = Path("uploads")
    PROCESSED_DIR: Path = Path("processed")

    class Config:
        env_file = ".env"

settings = Settings()

# Ensure directories exist at startup
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.PROCESSED_DIR.mkdir(exist_ok=True)