import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from pydantic import Field
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models import (
    AIAnalysis,
    AIAnalysisStatus,
    AIErrorCategory,
    AIFunctionType,
    AIModelSettings,
    AIResultLanguage,
    Client,
    Deal,
    EmailDraft,
    PipelineStage,
    User,
    UserRole,
)
from backend.app.schemas.ai import StrictAIResult
from backend.app.services.ai.operations import (
    DuplicateInFlightOperationError,
    RetryPolicy,
    create_queued_analysis,
    execute_analysis,
)
from backend.app.services.ai.provider import (
    ProviderFailure,
    ProviderResult,
    StructuredProviderRequest,
)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 against migrated development PostgreSQL",
)


@pytest.fixture
def isolated_database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[URL]:
    source_url = make_url(get_settings().database_url)
    database_name = f"vileoruf_crm_d41_test_{uuid4().hex}"
    maintenance_engine = create_engine(
        source_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    isolated_url = source_url.set(database=database_name)
    database_created = False

    try:
        with maintenance_engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
        database_created = True
        monkeypatch.setenv("DATABASE_URL", isolated_url.render_as_string(False))
        get_settings.cache_clear()
        yield isolated_url
    finally:
        get_settings.cache_clear()
        if database_created:
            with maintenance_engine.connect() as connection:
                connection.exec_driver_sql(
                    f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
                )
        maintenance_engine.dispose()


class SyntheticResult(StrictAIResult):
    score: int = Field(ge=0, le=100)


class _RetryThenSuccessProvider:
    def __init__(self) -> None:
        self.attempts = 0

    def generate_structured(
        self,
        request: StructuredProviderRequest,
        response_model: type[SyntheticResult],
    ) -> ProviderResult[SyntheticResult]:
        self.attempts += 1
        if self.attempts < 3:
            raise ProviderFailure(
                AIErrorCategory.PROVIDER_UNAVAILABLE,
                retryable=True,
            )
        return ProviderResult(
            result={"score": 77},
            actual_model=request.model,
            usage={"total_tokens": 20},
        )


def test_d41_migration_constraints_and_operation_lifecycle_on_postgresql(
    isolated_database_url: URL,
) -> None:
    alembic_config = Config("backend/alembic.ini")
    command.upgrade(alembic_config, "head")
    engine = create_engine(isolated_database_url)
    try:
        inspector = inspect(engine)
        assert {"ai_analyses", "email_drafts", "ai_model_settings"}.issubset(
            inspector.get_table_names()
        )
        enums = {enum["name"]: set(enum["labels"]) for enum in inspector.get_enums()}
        assert enums["ai_function_type"] == {item.value for item in AIFunctionType}
        assert enums["ai_analysis_status"] == {
            item.value for item in AIAnalysisStatus
        }
        assert enums["ai_result_language"] == {
            item.value for item in AIResultLanguage
        }
        assert enums["ai_error_category"] == {
            item.value for item in AIErrorCategory
        }
        analysis_indexes = {
            index["name"]: index for index in inspector.get_indexes("ai_analyses")
        }
        assert analysis_indexes["uq_ai_analyses_deal_function_inflight"][
            "unique"
        ] is True
        assert "postgresql_where" in analysis_indexes[
            "uq_ai_analyses_deal_function_inflight"
        ]["dialect_options"]

        with Session(engine, expire_on_commit=False) as session:
            manager = User(
                email="d41-manager@example.test",
                password_hash="$argon2id$synthetic-hash",
                display_name="D4.1 Manager",
                role=UserRole.MANAGER,
            )
            client = Client(name="D4.1 Client")
            stage = PipelineStage(name="D4.1 Stage", position=1)
            deal = Deal(name="D4.1 Deal", client=client, stage=stage)
            retry_deal = Deal(name="D4.1 Retry Deal", client=client, stage=stage)
            session.add_all([manager, deal, retry_deal])
            session.commit()

            lead_scoring = create_queued_analysis(
                session,
                deal_id=deal.id,
                function_type=AIFunctionType.LEAD_SCORING,
                language=AIResultLanguage.RU,
                prompt_version="ls-foundation-v1",
                significant_input={"deal": str(deal.id), "budget": None},
                snapshot_source={
                    "budget": None,
                    "description": "must not be stored",
                },
                snapshot_fields=("budget", "description"),
            )
            assert lead_scoring.input_snapshot == {"budget": None}

            with pytest.raises(DuplicateInFlightOperationError):
                create_queued_analysis(
                    session,
                    deal_id=deal.id,
                    function_type=AIFunctionType.LEAD_SCORING,
                    language=AIResultLanguage.EN,
                    prompt_version="ls-foundation-v1",
                    significant_input={"deal": str(deal.id)},
                    snapshot_source={},
                    snapshot_fields=(),
                )

            prediction = create_queued_analysis(
                session,
                deal_id=deal.id,
                function_type=AIFunctionType.DEAL_PREDICTION,
                language=AIResultLanguage.ES,
                prompt_version="dp-foundation-v1",
                significant_input={"deal": str(deal.id)},
                snapshot_source={"stage": "D4.1 Stage"},
                snapshot_fields=("stage",),
            )
            assert prediction.status is AIAnalysisStatus.QUEUED

            retry_analysis = create_queued_analysis(
                session,
                deal_id=retry_deal.id,
                function_type=AIFunctionType.LEAD_SCORING,
                language=AIResultLanguage.EN,
                prompt_version="ls-foundation-v1",
                significant_input={"deal": str(retry_deal.id)},
                snapshot_source={"stage": "D4.1 Stage"},
                snapshot_fields=("stage",),
            )
            row_id = retry_analysis.id
            provider = _RetryThenSuccessProvider()
            completed = execute_analysis(
                session,
                analysis=retry_analysis,
                provider=provider,
                request=StructuredProviderRequest(
                    model="gpt-5.4-mini",
                    trusted_instructions="Synthetic test instruction",
                    untrusted_business_data={"stage": "D4.1 Stage"},
                ),
                response_model=SyntheticResult,
                retry_policy=RetryPolicy(max_retries=2, backoff_seconds=0.001),
                sleeper=lambda _: None,
            )
            assert completed.id == row_id
            assert completed.status is AIAnalysisStatus.SUCCESS
            assert completed.attempt_count == 3
            assert completed.result_payload == {"score": 77}
            assert session.scalar(
                select(func.count()).select_from(AIAnalysis).where(
                    AIAnalysis.deal_id == retry_deal.id,
                    AIAnalysis.function_type == AIFunctionType.LEAD_SCORING,
                )
            ) == 1

            manual_draft = EmailDraft(
                deal_id=deal.id,
                subject="Manual subject",
                body="Editable manual body",
                language=AIResultLanguage.RU,
                purpose="custom",
                creator_user_id=manager.id,
            )
            sourced_draft = EmailDraft(
                deal_id=retry_deal.id,
                subject="AI subject",
                body="Editable AI body",
                language=AIResultLanguage.EN,
                purpose="follow-up",
                creator_user_id=manager.id,
                source_ai_analysis_id=completed.id,
            )
            session.add_all([manual_draft, sourced_draft])
            session.commit()
            assert manual_draft.source_ai_analysis_id is None
            assert sourced_draft.source_ai_analysis_id == completed.id

            invalid_success = AIAnalysis(
                deal_id=deal.id,
                function_type=AIFunctionType.NEXT_BEST_ACTION,
                status=AIAnalysisStatus.SUCCESS,
                language=AIResultLanguage.RU,
                prompt_version="nba-foundation-v1",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc) + timedelta(milliseconds=1),
                duration_ms=1,
                input_fingerprint="b" * 64,
                input_snapshot={},
                result_payload=None,
                attempt_count=1,
            )
            session.add(invalid_success)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(AIModelSettings(id=2))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

        command.downgrade(alembic_config, "20260901_0004")
        downgraded = inspect(create_engine(isolated_database_url))
        assert not {"ai_analyses", "email_drafts", "ai_model_settings"}.intersection(
            downgraded.get_table_names()
        )
        assert not {
            "ai_function_type",
            "ai_analysis_status",
            "ai_result_language",
            "ai_error_category",
        }.intersection({enum["name"] for enum in downgraded.get_enums()})

        command.upgrade(alembic_config, "head")
        assert {"ai_analyses", "email_drafts", "ai_model_settings"}.issubset(
            inspect(create_engine(isolated_database_url)).get_table_names()
        )
    finally:
        engine.dispose()
