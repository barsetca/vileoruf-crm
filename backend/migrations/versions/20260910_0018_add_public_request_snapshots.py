"""add immutable public request snapshots

Revision ID: 20260910_0018
Revises: 20260910_0017
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260910_0018"
down_revision = "20260910_0017"
branch_labels = None
depends_on = None


def upgrade():
    preferred_language = postgresql.ENUM(
        "RU", "EN", "ES", name="preferred_communication_language", create_type=False
    )
    op.create_table(
        "public_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("telegram", sa.String(length=255), nullable=True),
        sa.Column("whatsapp", sa.String(length=64), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("preferred_communication_language", preferred_language, nullable=False),
        sa.Column("deal_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("service_name_ru", sa.String(length=255), nullable=False),
        sa.Column("service_name_en", sa.String(length=255), nullable=False),
        sa.Column("service_name_es", sa.String(length=255), nullable=False),
        sa.Column("estimated_budget", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("personal_data_consent", sa.Boolean(), nullable=False),
        sa.Column("personal_data_consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("personal_data_consent_version", sa.String(length=32), nullable=False),
        sa.Column("privacy_policy_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deal_id"),
    )
    op.create_index("ix_public_requests_client_id", "public_requests", ["client_id"])
    op.create_index("ix_public_requests_service_id", "public_requests", ["service_id"])


def downgrade():
    op.drop_index("ix_public_requests_service_id", table_name="public_requests")
    op.drop_index("ix_public_requests_client_id", table_name="public_requests")
    op.drop_table("public_requests")
