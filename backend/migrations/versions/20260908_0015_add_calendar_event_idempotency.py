"""add calendar event idempotency

Revision ID: 20260908_0015
Revises: 20260907_0014
"""
from alembic import op
import sqlalchemy as sa

revision = "20260908_0015"
down_revision = "20260907_0014"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("calendar_events", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.create_unique_constraint("uq_calendar_events_connection_idempotency_key", "calendar_events", ["integration_connection_id", "idempotency_key"])

def downgrade():
    op.drop_constraint("uq_calendar_events_connection_idempotency_key", "calendar_events", type_="unique")
    op.drop_column("calendar_events", "idempotency_key")
