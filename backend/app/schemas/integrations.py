from datetime import datetime
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, StringConstraints
from backend.app.models.integrations import IntegrationConnectionStatus, IntegrationProvider

class IntegrationConnectionResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID | None = None
    provider: IntegrationProvider
    status: IntegrationConnectionStatus
    display_name: str
    external_account_id: str | None = None
    external_account_email: str | None = None
    connected_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_code: str | None = None
    inbound_sync_status: str = "IDLE"
    last_inbound_sync_at: datetime | None = None
    inbound_sync_error_code: str | None = None


class GoogleOAuthStartResponse(BaseModel):
    authorization_url: str


class GmailSyncStartResponse(BaseModel):
    status: str


class TelegramConfigurationResponse(BaseModel):
    status: str


class TelegramAvailabilityResponse(BaseModel):
    provider: IntegrationProvider = IntegrationProvider.TELEGRAM
    available: bool


class TelegramMessageCreate(BaseModel):
    client_id: UUID
    deal_id: UUID | None = None
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TelegramMessageLink(BaseModel):
    client_id: UUID
