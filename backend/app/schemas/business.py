from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


LocalizedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
PositiveHours = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_ru: LocalizedName
    name_en: LocalizedName
    name_es: LocalizedName
    target_hourly_rate: PositiveMoney
    target_effort: PositiveHours


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_ru: LocalizedName | None = None
    name_en: LocalizedName | None = None
    name_es: LocalizedName | None = None
    target_hourly_rate: PositiveMoney | None = None
    target_effort: PositiveHours | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Category fields cannot be null")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name_ru: str
    name_en: str
    name_es: str
    is_active: bool
    target_hourly_rate: Decimal
    target_effort: Decimal
    created_at: datetime
    updated_at: datetime


class ServiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_id: UUID
    name_ru: LocalizedName
    name_en: LocalizedName
    name_es: LocalizedName


class ServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_id: UUID | None = None
    name_ru: LocalizedName | None = None
    name_en: LocalizedName | None = None
    name_es: LocalizedName | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Service fields cannot be null")
        return self


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    category_id: UUID
    name_ru: str
    name_en: str
    name_es: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CommercialValuePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ratio: Decimal = Field(gt=0)
    score: int = Field(ge=0, le=100)


class LeadScoringSettingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_fit_weight: int = Field(ge=0, le=100)
    commercial_value_weight: int = Field(ge=0, le=100)
    lead_quality_weight: int = Field(ge=0, le=100)
    feasibility_weight: int = Field(ge=0, le=100)
    commercial_value_scale: list[CommercialValuePoint] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def validate_business_rules(self):
        if sum((self.service_fit_weight, self.commercial_value_weight, self.lead_quality_weight, self.feasibility_weight)) != 100:
            raise ValueError("Lead Scoring weights must total exactly 100")
        ratios = [point.ratio for point in self.commercial_value_scale]
        scores = [point.score for point in self.commercial_value_scale]
        if ratios != sorted(ratios) or len(set(ratios)) != len(ratios):
            raise ValueError("Commercial Value ratios must be unique and strictly increasing")
        if scores != sorted(scores):
            raise ValueError("Commercial Value scores must be non-decreasing")
        return self


class LeadScoringSettingsResponse(LeadScoringSettingsPayload):
    updated_at: datetime
