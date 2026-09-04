"""Create D4.2 business configuration and Deal/Client fields.

Revision ID: 20260902_0006
Revises: 20260902_0005
Create Date: 2026-09-02
"""

from collections.abc import Sequence
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260902_0006"
down_revision: str | None = "20260902_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_SCALE = [
    {"ratio": "0.50", "score": 0},
    {"ratio": "0.75", "score": 40},
    {"ratio": "1.00", "score": 70},
    {"ratio": "1.25", "score": 85},
    {"ratio": "1.50", "score": 100},
]


def upgrade() -> None:
    language = postgresql.ENUM("RU", "EN", "ES", name="preferred_communication_language", create_type=False)
    language.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_es", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("target_hourly_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_effort", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_hourly_rate > 0", name="ck_categories_target_hourly_rate_positive"),
        sa.CheckConstraint("target_effort > 0", name="ck_categories_target_effort_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_ru"),
    )
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("name_es", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name_ru"),
    )
    op.create_index("ix_services_category_id", "services", ["category_id"])
    op.create_table(
        "lead_scoring_settings",
        sa.Column("id", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("service_fit_weight", sa.SmallInteger(), server_default=sa.text("30"), nullable=False),
        sa.Column("commercial_value_weight", sa.SmallInteger(), server_default=sa.text("30"), nullable=False),
        sa.Column("lead_quality_weight", sa.SmallInteger(), server_default=sa.text("15"), nullable=False),
        sa.Column("feasibility_weight", sa.SmallInteger(), server_default=sa.text("25"), nullable=False),
        sa.Column("commercial_value_scale", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_lead_scoring_settings_singleton"),
        sa.CheckConstraint("service_fit_weight + commercial_value_weight + lead_quality_weight + feasibility_weight = 100", name="ck_lead_scoring_settings_weights_total"),
        sa.CheckConstraint("service_fit_weight >= 0 AND commercial_value_weight >= 0 AND lead_quality_weight >= 0 AND feasibility_weight >= 0", name="ck_lead_scoring_settings_weights_non_negative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO lead_scoring_settings (id, commercial_value_scale) "
            "VALUES (1, CAST(:scale AS jsonb))"
        ).bindparams(sa.bindparam("scale", value=json.dumps(DEFAULT_SCALE), type_=sa.Text()))
    )

    op.add_column("clients", sa.Column("preferred_communication_language", language, server_default=sa.text("'RU'::preferred_communication_language"), nullable=False))
    op.add_column("deals", sa.Column("service_id", sa.Uuid(), nullable=True))
    op.add_column("deals", sa.Column("manager_effort_estimate", sa.Numeric(10, 2), nullable=True))
    op.create_foreign_key("fk_deals_service_id_services", "deals", "services", ["service_id"], ["id"])
    op.create_index("ix_deals_service_id", "deals", ["service_id"])
    op.create_check_constraint("ck_deals_estimated_budget_non_negative", "deals", "estimated_budget IS NULL OR estimated_budget >= 0")
    op.create_check_constraint("ck_deals_manager_effort_positive", "deals", "manager_effort_estimate IS NULL OR manager_effort_estimate > 0")


def downgrade() -> None:
    op.drop_constraint("ck_deals_manager_effort_positive", "deals", type_="check")
    op.drop_constraint("ck_deals_estimated_budget_non_negative", "deals", type_="check")
    op.drop_index("ix_deals_service_id", table_name="deals")
    op.drop_constraint("fk_deals_service_id_services", "deals", type_="foreignkey")
    op.drop_column("deals", "manager_effort_estimate")
    op.drop_column("deals", "service_id")
    op.drop_column("clients", "preferred_communication_language")
    op.drop_table("lead_scoring_settings")
    op.drop_index("ix_services_category_id", table_name="services")
    op.drop_table("services")
    op.drop_table("categories")
    postgresql.ENUM(name="preferred_communication_language").drop(op.get_bind(), checkfirst=True)
