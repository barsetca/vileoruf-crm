"""add deal first won timestamp

Revision ID: 20260909_0016
Revises: 20260908_0015
"""

from alembic import op
import sqlalchemy as sa


revision = "20260909_0016"
down_revision = "20260908_0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("deals", sa.Column("first_won_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("deals", "first_won_at")
