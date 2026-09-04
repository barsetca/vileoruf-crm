from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.core.config import AIInfrastructureSettings
from backend.app.models import AIErrorCategory, AIModelSettings
from backend.app.services.ai.inputs import (
    build_compact_snapshot,
    deterministic_input_fingerprint,
)
from backend.app.services.ai.model_settings import resolve_ai_models
from backend.app.services.ai.provider import ProviderFailure


def test_input_fingerprint_is_deterministic_and_sensitive_to_inputs() -> None:
    identifier = uuid4()
    first = {
        "deal_id": identifier,
        "budget": Decimal("1200.00"),
        "nested": {"stage": "Contact", "count": 2},
    }
    reordered = {
        "nested": {"count": 2, "stage": "Contact"},
        "budget": Decimal("1200.00"),
        "deal_id": identifier,
    }

    assert deterministic_input_fingerprint(first) == deterministic_input_fingerprint(
        reordered
    )
    assert deterministic_input_fingerprint(first) != deterministic_input_fingerprint(
        {**first, "budget": Decimal("1201.00")}
    )


def test_compact_snapshot_is_explicit_bounded_and_omits_free_text() -> None:
    source = {
        "budget": "1200",
        "description": "secret full description",
        "deal_description": "also forbidden",
        "prompt": "raw prompt",
        "nested": {
            "stage": "Contact",
            "content": "full communication",
            "notes": "x" * 500,
        },
        "unused": "not selected",
    }

    snapshot = build_compact_snapshot(
        source,
        include_fields=(
            "budget",
            "description",
            "deal_description",
            "prompt",
            "nested",
        ),
    )

    assert snapshot == {
        "budget": "1200",
        "nested": {"stage": "Contact", "notes": "x" * 256},
    }
    assert "secret full description" not in str(snapshot)
    assert "full communication" not in str(snapshot)


def test_ai_environment_defaults_and_allowlist_parsing() -> None:
    settings = AIInfrastructureSettings(_env_file=None)

    assert settings.ai_analysis_model == "gpt-5.4-mini"
    assert settings.ai_email_model == "gpt-5.4-mini"
    assert settings.allowed_models == (
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-5.4-nano",
    )
    assert settings.ai_max_retries == 2
    assert settings.openai_api_key is None


def test_ai_environment_values_are_parsed_without_requiring_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    monkeypatch.setenv("AI_MAX_RETRIES", "1")
    monkeypatch.setenv("AI_RETRY_BACKOFF_SECONDS", "0.5")
    monkeypatch.setenv("AI_MODEL_ALLOWLIST", "model-a, model-b,model-a")
    monkeypatch.setenv("AI_ANALYSIS_MODEL", "model-a")
    monkeypatch.setenv("AI_EMAIL_MODEL", "model-b")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = AIInfrastructureSettings(_env_file=None)

    assert settings.celery_task_always_eager is True
    assert settings.ai_max_retries == 1
    assert settings.ai_retry_backoff_seconds == 0.5
    assert settings.allowed_models == ("model-a", "model-b")
    assert settings.openai_api_key is None


def test_ai_environment_rejects_non_redis_transport_and_invalid_defaults() -> None:
    with pytest.raises(ValidationError):
        AIInfrastructureSettings(celery_broker_url="amqp://localhost")
    with pytest.raises(ValidationError):
        AIInfrastructureSettings(
            ai_analysis_model="not-allowed",
            ai_model_allowlist="gpt-5.4-mini",
        )


class _SettingsSession:
    def __init__(self, row: AIModelSettings | None) -> None:
        self.row = row

    def get(self, model: object, identifier: int) -> AIModelSettings | None:
        assert model is AIModelSettings
        assert identifier == 1
        return self.row


def test_db_model_overrides_take_precedence_and_reset_falls_back_to_env() -> None:
    settings = AIInfrastructureSettings()
    overrides = AIModelSettings(
        analysis_model_override="gpt-5.4",
        email_model_override="gpt-5.4-nano",
    )

    resolved = resolve_ai_models(_SettingsSession(overrides), settings)  # type: ignore[arg-type]
    reset = resolve_ai_models(_SettingsSession(None), settings)  # type: ignore[arg-type]

    assert resolved.analysis_model == "gpt-5.4"
    assert resolved.email_model == "gpt-5.4-nano"
    assert reset.analysis_model == "gpt-5.4-mini"
    assert reset.email_model == "gpt-5.4-mini"


def test_invalid_persisted_model_override_is_safe_configuration_error() -> None:
    with pytest.raises(ProviderFailure) as error:
        resolve_ai_models(  # type: ignore[arg-type]
            _SettingsSession(AIModelSettings(analysis_model_override="arbitrary")),
            AIInfrastructureSettings(),
        )

    assert error.value.category is AIErrorCategory.CONFIGURATION_ERROR
    assert error.value.retryable is False
