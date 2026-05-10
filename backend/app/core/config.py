import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    APP_ENV: str = "development"

    UPLOAD_DIR: Path = PROJECT_ROOT / "backend" / "uploads"
    PROCESSED_DIR: Path = PROJECT_ROOT / "backend" / "processed"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    print(f"Project Root: {settings.PROJECT_ROOT}")
