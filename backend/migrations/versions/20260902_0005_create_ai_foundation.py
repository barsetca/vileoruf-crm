"""Create Day 4 AI foundation persistence schema.

Revision ID: 20260902_0005
Revises: 20260901_0004
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260902_0005"
down_revision: str | None = "20260901_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    ai_function_type = postgresql.ENUM(
        "LEAD_SCORING",
        "DEAL_PREDICTION",
        "NEXT_BEST_ACTION",
        "EMAIL_DRAFT",
        name="ai_function_type",
        create_type=False,
    )
    ai_analysis_status = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        name="ai_analysis_status",
        create_type=False,
    )
    ai_result_language = postgresql.ENUM(
        "RU",
        "EN",
        "ES",
        name="ai_result_language",
        create_type=False,
    )
    ai_error_category = postgresql.ENUM(
        "PROVIDER_TIMEOUT",
        "PROVIDER_UNAVAILABLE",
        "INVALID_STRUCTURED_RESPONSE",
        "CONFIGURATION_ERROR",
        name="ai_error_category",
        create_type=False,
    )
    for enum_type in (
        ai_function_type,
        ai_analysis_status,
        ai_result_language,
        ai_error_category,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_model_settings",
        sa.Column(
            "id",
            sa.SmallInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("analysis_model_override", sa.String(length=128), nullable=True),
        sa.Column("email_model_override", sa.String(length=128), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="ck_ai_model_settings_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("function_type", ai_function_type, nullable=False),
        sa.Column(
            "status",
            ai_analysis_status,
            server_default=sa.text("'QUEUED'::ai_analysis_status"),
            nullable=False,
        ),
        sa.Column("actual_model", sa.String(length=128), nullable=True),
        sa.Column("language", ai_result_language, nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("provider_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_category", ai_error_category, nullable=True),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "is_outdated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.SmallInteger(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 3",
            name="ck_ai_analyses_attempt_count_range",
        ),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_ai_analyses_duration_non_negative",
        ),
        sa.CheckConstraint(
            "(status = 'QUEUED' AND started_at IS NULL) OR "
            "(status <> 'QUEUED' AND started_at IS NOT NULL)",
            name="ck_ai_analyses_started_lifecycle",
        ),
        sa.CheckConstraint(
            "(status IN ('QUEUED', 'RUNNING') AND finished_at IS NULL "
            "AND duration_ms IS NULL AND result_payload IS NULL "
            "AND error_category IS NULL AND is_outdated = false) OR "
            "(status = 'SUCCESS' AND finished_at IS NOT NULL "
            "AND duration_ms IS NOT NULL AND result_payload IS NOT NULL "
            "AND error_category IS NULL) OR "
            "(status = 'FAILED' AND finished_at IS NOT NULL "
            "AND duration_ms IS NOT NULL AND result_payload IS NULL "
            "AND error_category IS NOT NULL AND is_outdated = false)",
            name="ck_ai_analyses_terminal_payload",
        ),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyses_deal_id", "ai_analyses", ["deal_id"])
    op.create_index(
        "uq_ai_analyses_deal_function_inflight",
        "ai_analyses",
        ["deal_id", "function_type"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )

    op.create_table(
        "email_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", ai_result_language, nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=False),
        sa.Column("creator_user_id", sa.Uuid(), nullable=False),
        sa.Column("source_ai_analysis_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.ForeignKeyConstraint(["source_ai_analysis_id"], ["ai_analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_drafts_deal_id", "email_drafts", ["deal_id"])
    op.create_index(
        "ix_email_drafts_creator_user_id", "email_drafts", ["creator_user_id"]
    )
    op.create_index(
        "ix_email_drafts_source_ai_analysis_id",
        "email_drafts",
        ["source_ai_analysis_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_drafts_source_ai_analysis_id", table_name="email_drafts")
    op.drop_index("ix_email_drafts_creator_user_id", table_name="email_drafts")
    op.drop_index("ix_email_drafts_deal_id", table_name="email_drafts")
    op.drop_table("email_drafts")
    op.drop_index(
        "uq_ai_analyses_deal_function_inflight", table_name="ai_analyses"
    )
    op.drop_index("ix_ai_analyses_deal_id", table_name="ai_analyses")
    op.drop_table("ai_analyses")
    op.drop_table("ai_model_settings")
    postgresql.ENUM(name="ai_error_category").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="ai_result_language").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="ai_analysis_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="ai_function_type").drop(op.get_bind(), checkfirst=True)
