"""add public request consent metadata

Revision ID: 20260910_0017
Revises: 20260909_0016
"""

from alembic import op
import sqlalchemy as sa


revision = "20260910_0017"
down_revision = "20260909_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clients", sa.Column("personal_data_consent", sa.Boolean(), nullable=True))
    op.add_column("clients", sa.Column("personal_data_consent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("clients", sa.Column("personal_data_consent_version", sa.String(length=32), nullable=True))
    op.add_column("clients", sa.Column("privacy_policy_version", sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column("clients", "privacy_policy_version")
    op.drop_column("clients", "personal_data_consent_version")
    op.drop_column("clients", "personal_data_consent_at")
    op.drop_column("clients", "personal_data_consent")
