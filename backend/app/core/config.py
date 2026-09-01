from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AppEnvironment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    app_env: AppEnvironment
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


class SecuritySettings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: PositiveInt = 30
    refresh_token_expire_days: PositiveInt = 7
    auth_cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def require_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()


@lru_cache
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()
