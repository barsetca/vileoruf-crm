"""Add configurable Deal Prediction freshness period.

Revision ID: 20260903_0007
Revises: 20260902_0006
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_0007"
down_revision: str | None = "20260902_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_model_settings",
        sa.Column(
            "deal_prediction_validity_days",
            sa.SmallInteger(),
            server_default=sa.text("7"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_ai_model_settings_prediction_validity_positive",
        "ai_model_settings",
        "deal_prediction_validity_days > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ai_model_settings_prediction_validity_positive",
        "ai_model_settings",
        type_="check",
    )
    op.drop_column("ai_model_settings", "deal_prediction_validity_days")
