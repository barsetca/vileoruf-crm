from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.models import UserRole


class PipelineStageReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    position: int


class EmployeeReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    role: UserRole
    is_active: bool
