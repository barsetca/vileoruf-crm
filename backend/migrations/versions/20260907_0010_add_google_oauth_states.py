"""Add one-time Google OAuth state persistence.

Revision ID: 20260907_0010
Revises: 20260905_0009
"""
from alembic import op
import sqlalchemy as sa


revision = "20260907_0010"
down_revision = "20260905_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "integration_oauth_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("integration_connection_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["integration_connection_id"], ["integration_connections.id"]),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("state_hash", name="uq_integration_oauth_states_state_hash"),
    )
    op.create_index("ix_integration_oauth_states_state_hash", "integration_oauth_states", ["state_hash"])
    op.create_index("ix_integration_oauth_states_integration_connection_id", "integration_oauth_states", ["integration_connection_id"])
    op.create_index("ix_integration_oauth_states_initiated_by_user_id", "integration_oauth_states", ["initiated_by_user_id"])
    op.create_index("ix_integration_oauth_states_expires_at", "integration_oauth_states", ["expires_at"])


def downgrade():
    op.drop_index("ix_integration_oauth_states_expires_at", table_name="integration_oauth_states")
    op.drop_index("ix_integration_oauth_states_initiated_by_user_id", table_name="integration_oauth_states")
    op.drop_index("ix_integration_oauth_states_integration_connection_id", table_name="integration_oauth_states")
    op.drop_index("ix_integration_oauth_states_state_hash", table_name="integration_oauth_states")
    op.drop_table("integration_oauth_states")
