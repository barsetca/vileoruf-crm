from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from backend.app.models import CalendarEventStatus

class CalendarEventCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title: Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=255)]
    description: str|None=None
    start_at: datetime
    end_at: datetime
    timezone: Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=64)]
    client_id: UUID|None=None
    deal_id: UUID|None=None
    task_id: UUID|None=None
    @field_validator("start_at","end_at")
    @classmethod
    def aware(cls,value):
        if value.tzinfo is None or value.utcoffset() is None: raise ValueError("Calendar timestamps must include a timezone")
        return value
    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls,value):
        try: return ZoneInfo(value).key
        except ZoneInfoNotFoundError as error: raise ValueError("Calendar timezone must be an IANA timezone") from error
    @model_validator(mode="after")
    def valid_range(self):
        if self.end_at <= self.start_at: raise ValueError("Calendar end_at must be after start_at")
        return self


class CalendarEventUpdate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title: Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=255)]|None=None
    description: str|None=None
    start_at: datetime|None=None
    end_at: datetime|None=None
    timezone: Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=64)]|None=None
    @field_validator("start_at","end_at")
    @classmethod
    def aware(cls,value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None): raise ValueError("Calendar timestamps must include a timezone")
        return value
    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls,value):
        if value is None: return value
        try: return ZoneInfo(value).key
        except ZoneInfoNotFoundError as error: raise ValueError("Calendar timezone must be an IANA timezone") from error
    @model_validator(mode="after")
    def valid_update(self):
        if not self.model_fields_set: raise ValueError("Calendar update is required")
        if any(getattr(self,field) is None for field in ("title","start_at","end_at","timezone") if field in self.model_fields_set): raise ValueError("Calendar update fields cannot be null")
        if self.start_at is not None and self.end_at is not None and self.end_at <= self.start_at: raise ValueError("Calendar end_at must be after start_at")
        return self

class CalendarEventResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; integration_connection_id: UUID; client_id: UUID|None; deal_id: UUID|None; task_id: UUID|None
    provider_event_id: str|None; title: str; description: str|None; start_at: datetime; end_at: datetime; timezone: str
    status: CalendarEventStatus; external_url: str|None; last_synced_at: datetime|None; last_error_code: str|None; created_by_user_id: UUID; created_at: datetime; updated_at: datetime
