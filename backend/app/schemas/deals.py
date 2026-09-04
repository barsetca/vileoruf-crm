from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from backend.app.models import AIResultLanguage


DealName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
EstimatedBudget = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]
ManagerEffort = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Probability = Annotated[int, Field(ge=0, le=100)]


class DealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    stage_id: UUID
    responsible_user_id: UUID | None
    service_id: UUID | None
    name: str
    description: str | None
    estimated_budget: Decimal | None
    deadline: date | None
    probability: int | None
    manager_effort_estimate: Decimal | None
    created_at: datetime
    updated_at: datetime


class DealCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: UUID
    stage_id: UUID
    responsible_user_id: UUID | None = None
    service_id: UUID | None = None
    name: DealName
    description: str | None = None
    estimated_budget: EstimatedBudget | None = None
    deadline: date | None = None
    probability: Probability | None = None
    manager_effort_estimate: ManagerEffort | None = None
    ai_analysis_language: AIResultLanguage = AIResultLanguage.RU

    @model_validator(mode="after")
    def validate_new_deadline(self):
        if self.estimated_budget is not None and self.estimated_budget < 0:
            raise ValueError("Budget must be non-negative")
        if self.deadline is not None and self.deadline < date.today():
            raise ValueError("Desired deadline cannot be in the past")
        return self


class DealUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: DealName | None = None
    description: str | None = None
    estimated_budget: EstimatedBudget | None = None
    deadline: date | None = None
    probability: Probability | None = None
    responsible_user_id: UUID | None = None
    service_id: UUID | None = None
    manager_effort_estimate: ManagerEffort | None = None

    @model_validator(mode="after")
    def require_valid_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Deal name cannot be null")
        if self.estimated_budget is not None and self.estimated_budget < 0:
            raise ValueError("Budget must be non-negative")
        if "deadline" in self.model_fields_set and self.deadline is not None and self.deadline < date.today():
            raise ValueError("Desired deadline cannot be in the past")
        return self


class DealTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: UUID
