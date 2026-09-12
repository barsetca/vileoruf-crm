"""add client and deal archive timestamps

Revision ID: 20260910_0019
Revises: 20260910_0018
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_0019"
down_revision = "20260910_0018"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("clients", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_clients_archived_at", "clients", ["archived_at"])
    op.create_index("ix_deals_archived_at", "deals", ["archived_at"])

def downgrade():
    op.drop_index("ix_deals_archived_at", table_name="deals")
    op.drop_index("ix_clients_archived_at", table_name="clients")
    op.drop_column("deals", "archived_at")
    op.drop_column("clients", "archived_at")
