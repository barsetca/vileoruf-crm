from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, field_validator, model_validator
from typing import Annotated
from uuid import UUID

from backend.app.models import PreferredCommunicationLanguage


PublicName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
PublicBudget = Annotated[Decimal, Field(max_digits=14, decimal_places=2, ge=0)]


class PublicRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PublicName
    contact_person: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    whatsapp: str | None = None
    company: str | None = None
    deal_name: PublicName
    service_id: UUID
    description: str | None = None
    estimated_budget: PublicBudget | None = None
    deadline: date | None = None
    preferred_communication_language: PreferredCommunicationLanguage = PreferredCommunicationLanguage.RU
    personal_data_consent: StrictBool

    @field_validator("personal_data_consent")
    @classmethod
    def require_personal_data_consent(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Personal-data consent must be true")
        return value

    @model_validator(mode="after")
    def validate_deadline(self):
        if self.deadline is not None and self.deadline < date.today():
            raise ValueError("Desired deadline cannot be in the past")
        return self


class PublicRequestResponse(BaseModel):
    status: str = "accepted"


class PublicRequestSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    contact_person: str | None
    company: str | None
    email: str | None
    phone: str | None
    telegram: str | None
    whatsapp: str | None
    preferred_communication_language: PreferredCommunicationLanguage
    deal_name: str
    description: str | None
    service_name_ru: str
    service_name_en: str
    service_name_es: str
    estimated_budget: Decimal | None
    deadline: date | None
    created_at: datetime
