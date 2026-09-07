from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Enum as SqlEnum, Index
from sqlalchemy.dialects.postgresql import JSONB

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


def test_ai_analysis_model_matches_foundation_contract() -> None:
    columns = AIAnalysis.__table__.columns

    assert set(columns.keys()) == {
        "id",
        "deal_id",
        "function_type",
        "status",
        "actual_model",
        "language",
        "prompt_version",
        "started_at",
        "finished_at",
        "duration_ms",
        "provider_usage",
        "input_fingerprint",
        "input_snapshot",
        "error_category",
        "result_payload",
        "is_outdated",
        "attempt_count",
        "created_at",
        "updated_at",
    }
    assert isinstance(columns["function_type"].type, SqlEnum)
    assert set(columns["function_type"].type.enums) == {
        item.value for item in AIFunctionType
    }
    assert set(columns["status"].type.enums) == {
        item.value for item in AIAnalysisStatus
    }
    assert set(columns["language"].type.enums) == {
        item.value for item in AIResultLanguage
    }
    assert set(columns["error_category"].type.enums) == {
        item.value for item in AIErrorCategory
    }
    assert isinstance(columns["provider_usage"].type, JSONB)
    assert isinstance(columns["input_snapshot"].type, JSONB)
    assert isinstance(columns["result_payload"].type, JSONB)
    assert isinstance(columns["is_outdated"].type, Boolean)
    assert {fk.target_fullname for fk in columns["deal_id"].foreign_keys} == {
        "deals.id"
    }
    constraint_names = {
        constraint.name
        for constraint in AIAnalysis.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_ai_analyses_attempt_count_range",
        "ck_ai_analyses_duration_non_negative",
        "ck_ai_analyses_started_lifecycle",
        "ck_ai_analyses_terminal_payload",
    }.issubset(constraint_names)
    inflight_index = next(
        index
        for index in AIAnalysis.__table__.indexes
        if index.name == "uq_ai_analyses_deal_function_inflight"
    )
    assert isinstance(inflight_index, Index)
    assert inflight_index.unique is True
    assert inflight_index.dialect_options["postgresql"]["where"] is not None


def test_email_draft_and_model_override_foundations_are_separate_entities() -> None:
    draft_columns = EmailDraft.__table__.columns
    assert set(draft_columns.keys()) == {
        "id",
        "deal_id",
        "subject",
        "body",
        "language",
        "purpose",
        "creator_user_id",
        "source_ai_analysis_id",
        "state",
        "created_at",
        "updated_at",
    }
    assert {fk.target_fullname for fk in draft_columns["deal_id"].foreign_keys} == {
        "deals.id"
    }
    assert {
        fk.target_fullname for fk in draft_columns["creator_user_id"].foreign_keys
    } == {"users.id"}
    assert {
        fk.target_fullname
        for fk in draft_columns["source_ai_analysis_id"].foreign_keys
    } == {"ai_analyses.id"}
    assert set(AIModelSettings.__table__.columns.keys()) == {
        "id",
        "analysis_model_override",
        "email_model_override",
        "deal_prediction_validity_days",
        "next_best_action_validity_days",
        "ai_enabled",
        "automatic_new_deal_analysis",
        "updated_at",
    }


def test_ai_and_email_draft_relationships_support_manual_and_ai_drafts() -> None:
    client = Client(name="AI Foundation Client")
    stage = PipelineStage(name="AI Foundation Stage", position=1)
    deal = Deal(name="AI Foundation Deal", client=client, stage=stage)
    manager = User(
        email="ai-foundation@example.test",
        password_hash="$argon2id$synthetic-hash",
        display_name="AI Manager",
        role=UserRole.MANAGER,
    )
    analysis = AIAnalysis(
        deal=deal,
        function_type=AIFunctionType.EMAIL_DRAFT,
        status=AIAnalysisStatus.SUCCESS,
        language=AIResultLanguage.EN,
        prompt_version="email-v1",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        duration_ms=1,
        input_fingerprint="a" * 64,
        input_snapshot={"purpose": "follow-up"},
        result_payload={"subject": "Hello", "body": "Body"},
        attempt_count=1,
    )
    ai_draft = EmailDraft(
        deal=deal,
        subject="Hello",
        body="Editable body",
        language=AIResultLanguage.EN,
        purpose="follow-up",
        creator=manager,
        source_ai_analysis=analysis,
    )
    manual_draft = EmailDraft(
        deal=deal,
        subject="Manual",
        body="Manual body",
        language=AIResultLanguage.RU,
        purpose="custom",
        creator=manager,
    )

    assert analysis in deal.ai_analyses
    assert ai_draft in analysis.email_drafts
    assert ai_draft in deal.email_drafts and manual_draft in deal.email_drafts
    assert ai_draft in manager.email_drafts and manual_draft in manager.email_drafts
    assert manual_draft.source_ai_analysis is None
    assert ai_draft.id is None  # SQLAlchemy assigns the UUID on flush.
