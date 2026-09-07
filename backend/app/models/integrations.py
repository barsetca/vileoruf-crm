from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.client import Client
    from backend.app.models.communication import Communication
    from backend.app.models.deal import Deal
    from backend.app.models.task import Task
    from backend.app.models.user import User


class IntegrationProvider(str, Enum): GMAIL="GMAIL"; TELEGRAM="TELEGRAM"; GOOGLE_CALENDAR="GOOGLE_CALENDAR"; WHATSAPP="WHATSAPP"
class IntegrationConnectionStatus(str, Enum): DISCONNECTED="DISCONNECTED"; CONNECTING="CONNECTING"; CONNECTED="CONNECTED"; ERROR="ERROR"
class ExternalMessageStatus(str, Enum): PENDING="PENDING"; SENT="SENT"; RECEIVED="RECEIVED"; FAILED="FAILED"; UNKNOWN="UNKNOWN"
class CalendarEventStatus(str, Enum): PENDING="PENDING"; SYNCED="SYNCED"; CANCELLED="CANCELLED"; ERROR="ERROR"

class IntegrationConnection(Base):
    __tablename__="integration_connections"
    __table_args__=(UniqueConstraint("provider", name="uq_integration_connections_provider"),)
    id: Mapped[UUID]=mapped_column(Uuid,primary_key=True,default=uuid4)
    provider: Mapped[IntegrationProvider]=mapped_column(SqlEnum(IntegrationProvider,name="integration_provider"),nullable=False)
    status: Mapped[IntegrationConnectionStatus]=mapped_column(SqlEnum(IntegrationConnectionStatus,name="integration_connection_status"),nullable=False,default=IntegrationConnectionStatus.DISCONNECTED)
    display_name: Mapped[str]=mapped_column(String(255),nullable=False)
    external_account_id: Mapped[str|None]=mapped_column(String(255)); external_account_email: Mapped[str|None]=mapped_column(String(320))
    connected_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_success_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_error_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_error_code: Mapped[str|None]=mapped_column(String(64))
    encrypted_token_payload: Mapped[str|None]=mapped_column(Text, nullable=True)
    inbound_sync_after: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    inbound_sync_page_token: Mapped[str|None]=mapped_column(String(512))
    inbound_sync_status: Mapped[str]=mapped_column(String(16), nullable=False, default="IDLE", server_default="IDLE")
    last_inbound_sync_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    inbound_sync_error_code: Mapped[str|None]=mapped_column(String(64))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,onupdate=utc_now,server_default=func.now())
    external_messages: Mapped[list["ExternalMessage"]]=relationship(back_populates="integration_connection")
    calendar_events: Mapped[list["CalendarEvent"]]=relationship(back_populates="integration_connection")
    oauth_states: Mapped[list["IntegrationOAuthState"]]=relationship(back_populates="integration_connection")

class IntegrationOAuthState(Base):
    __tablename__="integration_oauth_states"
    __table_args__=(UniqueConstraint("state_hash",name="uq_integration_oauth_states_state_hash"),)
    id: Mapped[UUID]=mapped_column(Uuid,primary_key=True,default=uuid4)
    state_hash: Mapped[str]=mapped_column(String(64),nullable=False,index=True)
    integration_connection_id: Mapped[UUID]=mapped_column(ForeignKey("integration_connections.id"),nullable=False,index=True)
    initiated_by_user_id: Mapped[UUID]=mapped_column(ForeignKey("users.id"),nullable=False,index=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,index=True)
    consumed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,server_default=func.now())
    integration_connection: Mapped["IntegrationConnection"]=relationship(back_populates="oauth_states")

class ExternalMessage(Base):
    __tablename__="external_messages"
    __table_args__=(UniqueConstraint("integration_connection_id","provider_message_id",name="uq_external_messages_connection_provider_message"),UniqueConstraint("integration_connection_id","idempotency_key",name="uq_external_messages_connection_idempotency_key"),)
    id: Mapped[UUID]=mapped_column(Uuid,primary_key=True,default=uuid4); integration_connection_id: Mapped[UUID]=mapped_column(ForeignKey("integration_connections.id"),nullable=False,index=True)
    provider: Mapped[IntegrationProvider]=mapped_column(SqlEnum(IntegrationProvider,name="integration_provider",create_type=False),nullable=False); provider_message_id: Mapped[str|None]=mapped_column(String(255)); provider_thread_id: Mapped[str|None]=mapped_column(String(255)); idempotency_key: Mapped[str|None]=mapped_column(String(128), nullable=True)
    client_id: Mapped[UUID|None]=mapped_column(ForeignKey("clients.id"),index=True); deal_id: Mapped[UUID|None]=mapped_column(ForeignKey("deals.id"),index=True); email_draft_id: Mapped[UUID|None]=mapped_column(ForeignKey("email_drafts.id"),index=True, unique=True); communication_id: Mapped[UUID|None]=mapped_column(ForeignKey("communications.id"),index=True, unique=True)
    direction: Mapped[str]=mapped_column(String(16),nullable=False); status: Mapped[ExternalMessageStatus]=mapped_column(SqlEnum(ExternalMessageStatus,name="external_message_status"),nullable=False); sender_identifier: Mapped[str]=mapped_column(String(320),nullable=False); recipient_identifier: Mapped[str]=mapped_column(String(320),nullable=False); subject: Mapped[str|None]=mapped_column(String(998)); content: Mapped[str]=mapped_column(Text,nullable=False)
    provider_created_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); received_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); sent_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_error_code: Mapped[str|None]=mapped_column(String(64)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,onupdate=utc_now,server_default=func.now())
    integration_connection: Mapped["IntegrationConnection"]=relationship(back_populates="external_messages")

class CalendarEvent(Base):
    __tablename__="calendar_events"
    id: Mapped[UUID]=mapped_column(Uuid,primary_key=True,default=uuid4); integration_connection_id: Mapped[UUID]=mapped_column(ForeignKey("integration_connections.id"),nullable=False,index=True); client_id: Mapped[UUID|None]=mapped_column(ForeignKey("clients.id"),index=True); deal_id: Mapped[UUID|None]=mapped_column(ForeignKey("deals.id"),index=True); task_id: Mapped[UUID|None]=mapped_column(ForeignKey("tasks.id"),index=True)
    provider_event_id: Mapped[str|None]=mapped_column(String(255)); title: Mapped[str]=mapped_column(String(255),nullable=False); description: Mapped[str|None]=mapped_column(Text); start_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False); end_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False); timezone: Mapped[str]=mapped_column(String(64),nullable=False); status: Mapped[CalendarEventStatus]=mapped_column(SqlEnum(CalendarEventStatus,name="calendar_event_status"),nullable=False); external_url: Mapped[str|None]=mapped_column(String(2048)); last_synced_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True)); last_error_code: Mapped[str|None]=mapped_column(String(64)); created_by_user_id: Mapped[UUID]=mapped_column(ForeignKey("users.id"),nullable=False,index=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,server_default=func.now()); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=utc_now,onupdate=utc_now,server_default=func.now())
    integration_connection: Mapped["IntegrationConnection"]=relationship(back_populates="calendar_events")
