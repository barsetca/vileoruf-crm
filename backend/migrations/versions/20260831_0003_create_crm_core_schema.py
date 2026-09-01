"""Create CRM core schema.

Revision ID: 20260831_0003
Revises: 20260829_0002
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260831_0003"
down_revision: str | None = "20260829_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    client_status = postgresql.ENUM(
        "CUSTOMER",
        "CLIENT",
        name="client_status",
        create_type=False,
    )
    client_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("telegram", sa.String(length=255), nullable=True),
        sa.Column("whatsapp", sa.String(length=64), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("lead_source", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            client_status,
            server_default=sa.text("'CUSTOMER'::client_status"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pipeline_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("position"),
    )

    op.create_table(
        "deals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_budget", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("stage_id", sa.Uuid(), nullable=False),
        sa.Column("probability", sa.SmallInteger(), nullable=True),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("responsible_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "probability >= 0 AND probability <= 100",
            name="ck_deals_probability_range",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["stage_id"], ["pipeline_stages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deals_client_id", "deals", ["client_id"])
    op.create_index(
        "ix_deals_responsible_user_id", "deals", ["responsible_user_id"]
    )
    op.create_index("ix_deals_stage_id", "deals", ["stage_id"])


def downgrade() -> None:
    op.drop_index("ix_deals_stage_id", table_name="deals")
    op.drop_index("ix_deals_responsible_user_id", table_name="deals")
    op.drop_index("ix_deals_client_id", table_name="deals")
    op.drop_table("deals")
    op.drop_table("pipeline_stages")
    op.drop_table("clients")
    postgresql.ENUM(name="client_status").drop(op.get_bind(), checkfirst=True)
