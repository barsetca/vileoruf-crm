"""add stable Telegram provider user identity to clients

Revision ID: 20260907_0013
Revises: 20260907_0012
"""

from alembic import op
import sqlalchemy as sa

revision = "20260907_0013"
down_revision = "20260907_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("telegram_provider_user_id", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_clients_telegram_provider_user_id", "clients", ["telegram_provider_user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_clients_telegram_provider_user_id", "clients", type_="unique")
    op.drop_column("clients", "telegram_provider_user_id")
