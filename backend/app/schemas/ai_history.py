from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models import AIAnalysisStatus, AIErrorCategory, AIFunctionType, AIResultLanguage
from backend.app.schemas.ai import DealPredictionAIResult, EmailDraftAIResult, LeadScoringResult, NextBestActionAIResult


AIHistoryResult = LeadScoringResult | DealPredictionAIResult | NextBestActionAIResult | EmailDraftAIResult


class SafeProviderUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class AIHistoryItem(BaseModel):
    id: UUID
    deal_id: UUID
    deal_name: str
    function_type: AIFunctionType
    status: AIAnalysisStatus
    language: AIResultLanguage
    actual_model: str | None
    error_category: AIErrorCategory | None
    result_payload: AIHistoryResult | None
    result_valid: bool | None
    is_outdated: bool
    is_current: bool
    attempt_count: int
    provider_usage: SafeProviderUsage | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None


class AIHistoryPage(BaseModel):
    items: list[AIHistoryItem]
    total: int
    limit: int
    offset: int
