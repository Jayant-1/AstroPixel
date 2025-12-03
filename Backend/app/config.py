"""
Configuration management for NASA Gigapixel Explorer API
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path
from typing import List, Union
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "NASA Gigapixel Explorer API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # Set to False for production
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    # Database
    # A sensible default for local development; production should set DATABASE_URL
    DATABASE_URL: str = "sqlite:///./nasa_explorer.db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "nasa_explorer"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    TILES_DIR: Path = BASE_DIR / "tiles"
    DATASETS_DIR: Path = BASE_DIR / "datasets"
    TEMP_DIR: Path = BASE_DIR / "temp"

    # Tile Settings
    TILE_SIZE: int = 256
    TILE_FORMAT: str = "jpg"
    TILE_QUALITY: int = 85
    MAX_ZOOM: int = 20
    GDAL_PROCESSES: int = 4

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Upload
    MAX_UPLOAD_SIZE: int = 42949672960  # 40GB
    MAX_REQUEST_BODY_SIZE: int = 42949672960  # 40GB (for Starlette)

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Cloud Storage (Cloudflare R2 / AWS S3)
    USE_S3: bool = False
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_BUCKET_NAME: str = ""
    AWS_REGION: str = "auto"  # Use 'auto' for R2
    S3_ENDPOINT_URL: str = ""  # R2 endpoint: https://<account_id>.r2.cloudflarestorage.com
    R2_PUBLIC_URL: str = ""  # Public bucket URL: https://pub-xxxx.r2.dev

    class Config:
        # Ensure the .env in the project root (Backend/.env) is loaded
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        for directory in [
            self.UPLOAD_DIR,
            self.TILES_DIR,
            self.DATASETS_DIR,
            self.TEMP_DIR,
        ]:
            directory.mkdir(exist_ok=True, parents=True)


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings
