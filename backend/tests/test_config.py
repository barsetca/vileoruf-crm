import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings


TEST_DATABASE_URL = "postgresql+psycopg://user:password@localhost/database"


@pytest.mark.parametrize("app_env", ["development", "test", "production"])
def test_settings_accepts_approved_app_environments(app_env: str) -> None:
    settings = Settings(app_env=app_env, database_url=TEST_DATABASE_URL)

    assert settings.app_env == app_env


def test_settings_rejects_unknown_app_environment() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(app_env="something_else", database_url=TEST_DATABASE_URL)

    assert error.value.errors()[0]["loc"] == ("app_env",)
    assert error.value.errors()[0]["type"] == "literal_error"


def test_get_settings_exposes_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()

    try:
        assert get_settings().app_env == "test"
    finally:
        get_settings.cache_clear()
