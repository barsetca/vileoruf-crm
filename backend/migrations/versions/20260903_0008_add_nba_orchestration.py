"""Add NBA settings and initial AI pipeline correlation.

Revision ID: 20260903_0008
Revises: 20260903_0007
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260903_0008"
down_revision: str | None = "20260903_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_model_settings", sa.Column("next_best_action_validity_days", sa.SmallInteger(), server_default=sa.text("7"), nullable=False))
    op.add_column("ai_model_settings", sa.Column("ai_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("ai_model_settings", sa.Column("automatic_new_deal_analysis", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.create_check_constraint("ck_ai_model_settings_nba_validity_positive", "ai_model_settings", "next_best_action_validity_days > 0")

    language = postgresql.ENUM("RU", "EN", "ES", name="ai_result_language", create_type=False)
    op.create_table(
        "initial_ai_analysis_pipelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("language", language, nullable=False),
        sa.Column("lead_scoring_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("deal_prediction_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("next_best_action_analysis_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.ForeignKeyConstraint(["lead_scoring_analysis_id"], ["ai_analyses.id"]),
        sa.ForeignKeyConstraint(["deal_prediction_analysis_id"], ["ai_analyses.id"]),
        sa.ForeignKeyConstraint(["next_best_action_analysis_id"], ["ai_analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deal_id"),
        sa.UniqueConstraint("lead_scoring_analysis_id"),
        sa.UniqueConstraint("deal_prediction_analysis_id"),
        sa.UniqueConstraint("next_best_action_analysis_id"),
    )
    op.create_index("ix_initial_ai_analysis_pipelines_deal_id", "initial_ai_analysis_pipelines", ["deal_id"])


def downgrade() -> None:
    op.drop_index("ix_initial_ai_analysis_pipelines_deal_id", table_name="initial_ai_analysis_pipelines")
    op.drop_table("initial_ai_analysis_pipelines")
    op.drop_constraint("ck_ai_model_settings_nba_validity_positive", "ai_model_settings", type_="check")
    op.drop_column("ai_model_settings", "automatic_new_deal_analysis")
    op.drop_column("ai_model_settings", "ai_enabled")
    op.drop_column("ai_model_settings", "next_best_action_validity_days")
