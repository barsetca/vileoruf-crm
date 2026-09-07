"""Create Day 5 integration foundation.

Revision ID: 20260905_0009
Revises: 20260903_0008
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260905_0009"
down_revision = "20260903_0008"
branch_labels = None
depends_on = None

def upgrade():
    provider = postgresql.ENUM("GMAIL","TELEGRAM","GOOGLE_CALENDAR","WHATSAPP", name="integration_provider"); provider.create(op.get_bind(), checkfirst=True)
    connection_status = postgresql.ENUM("DISCONNECTED","CONNECTING","CONNECTED","ERROR", name="integration_connection_status"); connection_status.create(op.get_bind(), checkfirst=True)
    message_status = postgresql.ENUM("PENDING","SENT","RECEIVED","FAILED","UNKNOWN", name="external_message_status"); message_status.create(op.get_bind(), checkfirst=True)
    event_status = postgresql.ENUM("PENDING","SYNCED","CANCELLED","ERROR", name="calendar_event_status"); event_status.create(op.get_bind(), checkfirst=True)
    draft_state = postgresql.ENUM("DRAFT","SENT", name="email_draft_state"); draft_state.create(op.get_bind(), checkfirst=True)
    provider = postgresql.ENUM("GMAIL","TELEGRAM","GOOGLE_CALENDAR","WHATSAPP", name="integration_provider", create_type=False)
    connection_status = postgresql.ENUM("DISCONNECTED","CONNECTING","CONNECTED","ERROR", name="integration_connection_status", create_type=False)
    message_status = postgresql.ENUM("PENDING","SENT","RECEIVED","FAILED","UNKNOWN", name="external_message_status", create_type=False)
    event_status = postgresql.ENUM("PENDING","SYNCED","CANCELLED","ERROR", name="calendar_event_status", create_type=False)
    draft_state = postgresql.ENUM("DRAFT","SENT", name="email_draft_state", create_type=False)
    op.create_table("integration_connections", sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("provider",provider,nullable=False),sa.Column("status",connection_status,nullable=False),sa.Column("display_name",sa.String(255),nullable=False),sa.Column("external_account_id",sa.String(255)),sa.Column("external_account_email",sa.String(320)),sa.Column("connected_at",sa.DateTime(timezone=True)),sa.Column("last_success_at",sa.DateTime(timezone=True)),sa.Column("last_error_at",sa.DateTime(timezone=True)),sa.Column("last_error_code",sa.String(64)),sa.Column("encrypted_token_payload",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.UniqueConstraint("provider",name="uq_integration_connections_provider"))
    op.create_table("external_messages",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("integration_connection_id",sa.Uuid(),nullable=False),sa.Column("provider",provider,nullable=False),sa.Column("provider_message_id",sa.String(255)),sa.Column("provider_thread_id",sa.String(255)),sa.Column("client_id",sa.Uuid()),sa.Column("deal_id",sa.Uuid()),sa.Column("communication_id",sa.Uuid()),sa.Column("direction",sa.String(16),nullable=False),sa.Column("status",message_status,nullable=False),sa.Column("sender_identifier",sa.String(320),nullable=False),sa.Column("recipient_identifier",sa.String(320),nullable=False),sa.Column("subject",sa.String(998)),sa.Column("content",sa.Text(),nullable=False),sa.Column("provider_created_at",sa.DateTime(timezone=True)),sa.Column("received_at",sa.DateTime(timezone=True)),sa.Column("sent_at",sa.DateTime(timezone=True)),sa.Column("last_error_code",sa.String(64)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.ForeignKeyConstraint(["integration_connection_id"],["integration_connections.id"]),sa.ForeignKeyConstraint(["client_id"],["clients.id"]),sa.ForeignKeyConstraint(["deal_id"],["deals.id"]),sa.ForeignKeyConstraint(["communication_id"],["communications.id"]),sa.UniqueConstraint("integration_connection_id","provider_message_id",name="uq_external_messages_connection_provider_message"))
    op.create_table("calendar_events",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("integration_connection_id",sa.Uuid(),nullable=False),sa.Column("client_id",sa.Uuid()),sa.Column("deal_id",sa.Uuid()),sa.Column("task_id",sa.Uuid()),sa.Column("provider_event_id",sa.String(255)),sa.Column("title",sa.String(255),nullable=False),sa.Column("description",sa.Text()),sa.Column("start_at",sa.DateTime(timezone=True),nullable=False),sa.Column("end_at",sa.DateTime(timezone=True),nullable=False),sa.Column("timezone",sa.String(64),nullable=False),sa.Column("status",event_status,nullable=False),sa.Column("external_url",sa.String(2048)),sa.Column("last_synced_at",sa.DateTime(timezone=True)),sa.Column("last_error_code",sa.String(64)),sa.Column("created_by_user_id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.ForeignKeyConstraint(["integration_connection_id"],["integration_connections.id"]),sa.ForeignKeyConstraint(["client_id"],["clients.id"]),sa.ForeignKeyConstraint(["deal_id"],["deals.id"]),sa.ForeignKeyConstraint(["task_id"],["tasks.id"]),sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"]))
    for table, cols in (("external_messages",["integration_connection_id"]),("external_messages",["client_id"]),("external_messages",["deal_id"]),("external_messages",["communication_id"]),("calendar_events",["integration_connection_id"]),("calendar_events",["client_id"]),("calendar_events",["deal_id"]),("calendar_events",["task_id"]),("calendar_events",["created_by_user_id"])): op.create_index("ix_"+table+"_"+cols[0],table,cols)
    op.add_column("email_drafts",sa.Column("state",draft_state,server_default="DRAFT",nullable=False))

def downgrade():
    op.drop_column("email_drafts","state")
    for table, col in (("calendar_events","created_by_user_id"),("calendar_events","task_id"),("calendar_events","deal_id"),("calendar_events","client_id"),("calendar_events","integration_connection_id"),("external_messages","communication_id"),("external_messages","deal_id"),("external_messages","client_id"),("external_messages","integration_connection_id")): op.drop_index("ix_"+table+"_"+col,table_name=table)
    op.drop_table("calendar_events"); op.drop_table("external_messages"); op.drop_table("integration_connections")
    bind=op.get_bind()
    for name in ("email_draft_state","calendar_event_status","external_message_status","integration_connection_status","integration_provider"): postgresql.ENUM(name=name).drop(bind,checkfirst=True)
