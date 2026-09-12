"""add explicit incoming communication read state

Revision ID: 20260911_0021
Revises: 20260911_0020
"""
from alembic import op
import sqlalchemy as sa

revision = "20260911_0021"
down_revision = "20260911_0020"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("communications", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_communications_read_at", "communications", ["read_at"])
    op.execute("UPDATE communications SET read_at = occurred_at WHERE direction = 'INCOMING' AND read_at IS NULL")


def downgrade():
    op.drop_index("ix_communications_read_at", table_name="communications")
    op.drop_column("communications", "read_at")
