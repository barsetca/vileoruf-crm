"""Add bounded Gmail inbound synchronization checkpoint state.

Revision ID: 20260907_0012
Revises: 20260907_0011
"""

from alembic import op
import sqlalchemy as sa

revision = "20260907_0012"
down_revision = "20260907_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("integration_connections", sa.Column("inbound_sync_after", sa.DateTime(timezone=True)))
    op.add_column("integration_connections", sa.Column("inbound_sync_page_token", sa.String(512)))
    op.add_column("integration_connections", sa.Column("inbound_sync_status", sa.String(16), nullable=False, server_default="IDLE"))
    op.add_column("integration_connections", sa.Column("last_inbound_sync_at", sa.DateTime(timezone=True)))
    op.add_column("integration_connections", sa.Column("inbound_sync_error_code", sa.String(64)))


def downgrade():
    op.drop_column("integration_connections", "inbound_sync_error_code")
    op.drop_column("integration_connections", "last_inbound_sync_at")
    op.drop_column("integration_connections", "inbound_sync_status")
    op.drop_column("integration_connections", "inbound_sync_page_token")
    op.drop_column("integration_connections", "inbound_sync_after")
