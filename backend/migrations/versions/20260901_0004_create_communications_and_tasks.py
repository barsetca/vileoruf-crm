"""Create Communications and Tasks persistence schema.

Revision ID: 20260901_0004
Revises: 20260831_0003
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260901_0004"
down_revision: str | None = "20260831_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    communication_channel = postgresql.ENUM(
        "EMAIL",
        "TELEGRAM",
        "WHATSAPP",
        "MANUAL",
        "OTHER",
        name="communication_channel",
        create_type=False,
    )
    communication_direction = postgresql.ENUM(
        "INCOMING",
        "OUTGOING",
        name="communication_direction",
        create_type=False,
    )
    communication_status = postgresql.ENUM(
        "RECORDED",
        name="communication_status",
        create_type=False,
    )
    task_status = postgresql.ENUM(
        "OPEN",
        "COMPLETED",
        name="task_status",
        create_type=False,
    )
    for enum_type in (
        communication_channel,
        communication_direction,
        communication_status,
        task_status,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "communications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=True),
        sa.Column("channel", communication_channel, nullable=False),
        sa.Column("direction", communication_direction, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", communication_status, nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_communications_client_id", "communications", ["client_id"])
    op.create_index("ix_communications_deal_id", "communications", ["deal_id"])
    op.create_index("ix_communications_occurred_at", "communications", ["occurred_at"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            task_status,
            server_default=sa.text("'OPEN'::task_status"),
            nullable=False,
        ),
        sa.Column("responsible_user_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("deal_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"]),
        sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_client_id", "tasks", ["client_id"])
    op.create_index("ix_tasks_deal_id", "tasks", ["deal_id"])
    op.create_index(
        "ix_tasks_responsible_user_id", "tasks", ["responsible_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_responsible_user_id", table_name="tasks")
    op.drop_index("ix_tasks_deal_id", table_name="tasks")
    op.drop_index("ix_tasks_client_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_communications_occurred_at", table_name="communications")
    op.drop_index("ix_communications_deal_id", table_name="communications")
    op.drop_index("ix_communications_client_id", table_name="communications")
    op.drop_table("communications")
    postgresql.ENUM(name="task_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="communication_status").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="communication_direction").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="communication_channel").drop(
        op.get_bind(), checkfirst=True
    )
