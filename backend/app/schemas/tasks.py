from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from backend.app.models import TaskStatus


TaskTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    due_at: datetime
    status: TaskStatus
    responsible_user_id: UUID
    client_id: UUID | None
    deal_id: UUID | None


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle
    description: str | None = None
    due_at: datetime
    responsible_user_id: UUID
    client_id: UUID | None = None
    deal_id: UUID | None = None

    @field_validator("due_at")
    @classmethod
    def require_timezone_aware_due_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Task due timestamp must include a timezone")
        return value


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: TaskTitle | None = None
    description: str | None = None
    due_at: datetime | None = None
    responsible_user_id: UUID | None = None
    client_id: UUID | None = None
    deal_id: UUID | None = None

    @field_validator("due_at")
    @classmethod
    def require_timezone_aware_due_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Task due timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Task title cannot be null")
        if "due_at" in self.model_fields_set and self.due_at is None:
            raise ValueError("Task due timestamp cannot be null")
        if (
            "responsible_user_id" in self.model_fields_set
            and self.responsible_user_id is None
        ):
            raise ValueError("Task responsible user cannot be null")
        return self
