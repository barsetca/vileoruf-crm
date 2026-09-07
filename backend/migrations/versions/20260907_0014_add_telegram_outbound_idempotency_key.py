"""add Telegram outbound request idempotency key

Revision ID: 20260907_0014
Revises: 20260907_0013
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_0014"
down_revision = "20260907_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("external_messages", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint("uq_external_messages_connection_idempotency_key", "external_messages", ["integration_connection_id", "idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_external_messages_connection_idempotency_key", "external_messages", type_="unique")
    op.drop_column("external_messages", "idempotency_key")
