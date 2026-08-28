from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def require_postgresql_psycopg(cls, value: str) -> str:
        url = make_url(value)
        if url.drivername != "postgresql+psycopg":
            raise ValueError(
                "DATABASE_URL must use the postgresql+psycopg driver"
            )
        return value


class FrontendSettings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()
