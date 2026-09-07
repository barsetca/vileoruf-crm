"""Add EmailDraft outbound-send correlation and finalization uniqueness.

Revision ID: 20260907_0011
Revises: 20260907_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_0011"
down_revision = "20260907_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("external_messages", sa.Column("email_draft_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_external_messages_email_draft_id", "external_messages", "email_drafts", ["email_draft_id"], ["id"])
    op.create_index("ix_external_messages_email_draft_id", "external_messages", ["email_draft_id"], unique=True)
    op.drop_index("ix_external_messages_communication_id", table_name="external_messages")
    op.create_index("ix_external_messages_communication_id", "external_messages", ["communication_id"], unique=True)


def downgrade():
    op.drop_index("ix_external_messages_communication_id", table_name="external_messages")
    op.create_index("ix_external_messages_communication_id", "external_messages", ["communication_id"])
    op.drop_index("ix_external_messages_email_draft_id", table_name="external_messages")
    op.drop_constraint("fk_external_messages_email_draft_id", "external_messages", type_="foreignkey")
    op.drop_column("external_messages", "email_draft_id")
