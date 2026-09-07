from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt, SecretStr, field_validator, model_validator
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


class AIInfrastructureSettings(BaseSettings):
    celery_broker_url: str = "redis://127.0.0.1:56379/0"
    celery_result_backend: str = "redis://127.0.0.1:56379/1"
    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = True
    openai_api_key: SecretStr | None = None
    openai_timeout_seconds: PositiveFloat = 30.0
    ai_max_retries: int = Field(default=2, ge=0, le=2)
    ai_retry_backoff_seconds: PositiveFloat = 2.0
    ai_communication_context_char_limit: PositiveInt = 12000
    ai_analysis_model: str = "gpt-5.4-mini"
    ai_email_model: str = "gpt-5.4-mini"
    ai_model_allowlist: str = "gpt-5.4-mini,gpt-5.4,gpt-5.4-nano"
    ai_rate_limit_requests: int = Field(default=10, ge=1, le=1000)
    ai_rate_limit_window_seconds: int = Field(default=60, ge=1, le=86400)

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_models(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.strip()
                for item in self.ai_model_allowlist.split(",")
                if item.strip()
            )
        )

    @field_validator(
        "celery_broker_url",
        "celery_result_backend",
        "ai_analysis_model",
        "ai_email_model",
        "ai_model_allowlist",
    )
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("AI infrastructure setting must not be empty")
        return value

    @field_validator("celery_broker_url", "celery_result_backend")
    @classmethod
    def require_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            raise ValueError("Celery broker/backend URL must use Redis")
        return value

    @model_validator(mode="after")
    def require_defaults_in_allowlist(self) -> "AIInfrastructureSettings":
        if not self.allowed_models:
            raise ValueError("AI_MODEL_ALLOWLIST must contain at least one model")
        for model in (self.ai_analysis_model, self.ai_email_model):
            if model not in self.allowed_models:
                raise ValueError("Default AI models must be present in AI_MODEL_ALLOWLIST")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()


@lru_cache
def get_security_settings() -> SecuritySettings:
    return SecuritySettings()


@lru_cache
def get_ai_infrastructure_settings() -> AIInfrastructureSettings:
    return AIInfrastructureSettings()

class IntegrationSecuritySettings(BaseSettings):
    integration_token_encryption_key: SecretStr | None = None
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_integration_security_settings() -> IntegrationSecuritySettings:
    return IntegrationSecuritySettings()


class GoogleOAuthSettings(BaseSettings):
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: str = "http://localhost:8000/settings/integrations/google/callback"
    google_oauth_state_ttl_seconds: PositiveInt = 600

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("google_oauth_redirect_uri")
    @classmethod
    def require_http_redirect_uri(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("GOOGLE_OAUTH_REDIRECT_URI must use HTTP(S)")
        return value


@lru_cache
def get_google_oauth_settings() -> GoogleOAuthSettings:
    return GoogleOAuthSettings()


class TelegramSettings(BaseSettings):
    telegram_bot_token: SecretStr | None = None
    telegram_webhook_secret: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_telegram_settings() -> TelegramSettings:
    return TelegramSettings()
