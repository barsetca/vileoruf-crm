"""add Telegram sender display metadata

Revision ID: 20260911_0022
Revises: 20260911_0021
"""
from alembic import op
import sqlalchemy as sa

revision = "20260911_0022"
down_revision = "20260911_0021"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("external_messages", sa.Column("sender_username", sa.String(length=255), nullable=True))
    op.add_column("external_messages", sa.Column("sender_first_name", sa.String(length=255), nullable=True))
    op.add_column("external_messages", sa.Column("sender_last_name", sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column("external_messages", "sender_last_name")
    op.drop_column("external_messages", "sender_first_name")
    op.drop_column("external_messages", "sender_username")
