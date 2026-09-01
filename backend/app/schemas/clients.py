from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from backend.app.models import ClientStatus


ClientName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
ContactPerson = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=320)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]
Telegram = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
WhatsApp = Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)]
Company = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
LeadSource = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contact_person: str | None
    email: str | None
    phone: str | None
    telegram: str | None
    whatsapp: str | None
    company: str | None
    lead_source: str | None
    notes: str | None
    status: ClientStatus
    created_at: datetime
    updated_at: datetime


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ClientName
    contact_person: ContactPerson | None = None
    email: Email | None = None
    phone: Phone | None = None
    telegram: Telegram | None = None
    whatsapp: WhatsApp | None = None
    company: Company | None = None
    lead_source: LeadSource | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ClientName | None = None
    contact_person: ContactPerson | None = None
    email: Email | None = None
    phone: Phone | None = None
    telegram: Telegram | None = None
    whatsapp: WhatsApp | None = None
    company: Company | None = None
    lead_source: LeadSource | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Client name cannot be null")
        return self
