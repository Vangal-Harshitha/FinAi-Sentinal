"""
core/config.py — Centralised application settings loaded from .env
"""
import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR    = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    # App
    APP_NAME: str = "FinAI"
    APP_VERSION: str = "9.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://finai_user:finai_pass@localhost:5432/finai_db"
    DATABASE_URL_SYNC: str = "postgresql://finai_user:finai_pass@localhost:5432/finai_db"

    # Security
    SECRET_KEY: str = "change-me-in-production-use-32-char-minimum"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage
    UPLOAD_DIR: str = str(BACKEND_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10

    # AI / ML
    ML_MODELS_DIR: str = str(ROOT_DIR / "ml_models")
    FINBERT_MODEL: str = "ProsusAI/finbert"
    WHISPER_MODEL: str = "base"
    OCR_ENGINE: str = "paddleocr"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
