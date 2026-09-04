from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing import Annotated


ModelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
ValidityDays = Annotated[int, Field(ge=1, le=365)]


class AISettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_enabled: bool | None = None
    automatic_new_deal_analysis: bool | None = None
    analysis_model_override: ModelName | None = None
    email_model_override: ModelName | None = None
    deal_prediction_validity_days: ValidityDays | None = None
    next_best_action_validity_days: ValidityDays | None = None

    @model_validator(mode="after")
    def require_non_null_non_model_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one AI setting must be provided")
        nullable = {"analysis_model_override", "email_model_override"}
        if any(field not in nullable and getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Only model overrides can be reset with null")
        return self


class AISettingsResponse(BaseModel):
    ai_enabled: bool
    automatic_new_deal_analysis: bool
    analysis_model_override: str | None
    effective_analysis_model: str
    default_analysis_model: str
    email_model_override: str | None
    effective_email_model: str
    default_email_model: str
    allowed_models: list[str]
    deal_prediction_validity_days: int
    default_deal_prediction_validity_days: int
    next_best_action_validity_days: int
    default_next_best_action_validity_days: int
