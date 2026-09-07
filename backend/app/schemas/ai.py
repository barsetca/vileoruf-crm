from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing import Annotated

from backend.app.models import AIAnalysisStatus, AIErrorCategory, AIResultLanguage, EmailDraftState, ExternalMessageStatus


class StrictAIResult(BaseModel):
    """Base for function-specific structured results added in D4.2-D4.5."""

    model_config = ConfigDict(extra="forbid")


Explanation = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class LeadScoringFactorAI(StrictAIResult):
    score: int = Field(ge=0, le=100)
    explanation: Explanation


class LeadScoringCategorySuggestionAI(StrictAIResult):
    category_name: str = Field(min_length=1, max_length=255)
    reason: Explanation


class LeadScoringAIResult(StrictAIResult):
    service_fit: LeadScoringFactorAI
    lead_quality: LeadScoringFactorAI
    feasibility: LeadScoringFactorAI
    summary: str = Field(min_length=1, max_length=1200)
    missing_data_observations: list[str] = Field(default_factory=list, max_length=10)
    security_warning: str | None = Field(default=None, max_length=1200)
    category_suggestion: LeadScoringCategorySuggestionAI | None = None


class LeadScoringFactorResult(StrictAIResult):
    score: Decimal = Field(ge=0, le=100)
    explanation: str


class CommercialValueResultSchema(LeadScoringFactorResult):
    status: str
    effective_effort: Decimal
    deal_hourly_rate: Decimal | None
    ratio: Decimal | None


class LeadScoringResult(StrictAIResult):
    overall_score: Decimal = Field(ge=0, le=100)
    service_fit: LeadScoringFactorResult
    commercial_value: CommercialValueResultSchema
    lead_quality: LeadScoringFactorResult
    feasibility: LeadScoringFactorResult
    summary: str
    missing_data: list[str]
    security_warning: str | None
    category_suggestion: LeadScoringCategorySuggestionAI | None


class LeadScoringLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: AIResultLanguage


class AIAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    deal_id: UUID
    status: AIAnalysisStatus
    language: AIResultLanguage
    actual_model: str | None
    error_category: AIErrorCategory | None
    result_payload: dict | None
    is_outdated: bool
    attempt_count: int
    created_at: datetime
    finished_at: datetime | None


class LeadScoringOverview(BaseModel):
    current: AIAnalysisResponse | None
    active: AIAnalysisResponse | None
    latest_attempt: AIAnalysisResponse | None
    history: list[AIAnalysisResponse]


class PredictionConfidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DealPredictionAIResult(StrictAIResult):
    probability_won: int = Field(ge=0, le=100)
    confidence: PredictionConfidence
    summary: str = Field(min_length=1, max_length=1200)
    positive_signals: list[Explanation] = Field(max_length=8)
    risks: list[Explanation] = Field(max_length=8)
    missing_context: list[Explanation] = Field(max_length=8)
    security_warning: str | None = Field(default=None, max_length=1200)


class DealPredictionLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: AIResultLanguage


class DealPredictionOverview(BaseModel):
    current: AIAnalysisResponse | None
    active: AIAnalysisResponse | None
    latest_attempt: AIAnalysisResponse | None
    history: list[AIAnalysisResponse]


class NextBestActionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NextBestActionItem(StrictAIResult):
    rank: int = Field(ge=1, le=3)
    priority: NextBestActionPriority
    action: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=1200)
    timing: str = Field(min_length=1, max_length=300)


class NextBestActionAIResult(StrictAIResult):
    actions: list[NextBestActionItem] = Field(min_length=1, max_length=3)
    summary: str = Field(min_length=1, max_length=1200)
    security_warning: str | None = Field(default=None, max_length=1200)

    @model_validator(mode="after")
    def require_ordered_sequential_ranks(self):
        ranks = [item.rank for item in self.actions]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("Action ranks must be ordered, unique, and sequential from 1")
        return self


class NextBestActionLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: AIResultLanguage


class NextBestActionOverview(BaseModel):
    current: AIAnalysisResponse | None
    active: AIAnalysisResponse | None
    latest_attempt: AIAnalysisResponse | None
    history: list[AIAnalysisResponse]
    waiting_for_initial_analyses: bool = False


EmailSubject = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=998)]
EmailBody = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)]
EmailPurpose = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
EmailInstructions = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2_000)]


class EmailDraftAIResult(StrictAIResult):
    subject: EmailSubject
    body: EmailBody
    security_warning: str | None = Field(default=None, max_length=1200)

    @model_validator(mode="after")
    def permit_only_the_client_name_placeholder(self):
        import re

        unsupported = re.search(r"\{\{(?!client_name\}\})[^{}]+\}\}", self.subject + "\n" + self.body)
        if unsupported:
            raise ValueError("Only {{client_name}} placeholder is supported")
        return self


class EmailDraftGenerationLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: EmailPurpose
    additional_instructions: EmailInstructions | None = None
    nba_analysis_id: UUID | None = None
    nba_action_rank: int | None = Field(default=None, ge=1, le=3)

    @model_validator(mode="after")
    def require_complete_nba_reference(self):
        if (self.nba_analysis_id is None) != (self.nba_action_rank is None):
            raise ValueError("NBA analysis id and action rank must be provided together")
        return self


class EmailGenerationResponse(AIAnalysisResponse):
    """Email analysis response with a server-rendered safe display variant."""


class EmailGenerationOverview(BaseModel):
    current: EmailGenerationResponse | None
    active: EmailGenerationResponse | None
    latest_attempt: EmailGenerationResponse | None
    history: list[EmailGenerationResponse]


class EmailDraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: EmailSubject
    body: EmailBody
    purpose: EmailPurpose
    language: AIResultLanguage | None = None
    source_ai_analysis_id: UUID | None = None


class EmailDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: EmailSubject | None = None
    body: EmailBody | None = None
    purpose: EmailPurpose | None = None
    language: AIResultLanguage | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class EmailDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deal_id: UUID
    subject: str
    body: str
    language: AIResultLanguage
    purpose: str
    creator_user_id: UUID
    source_ai_analysis_id: UUID | None
    state: EmailDraftState
    outbound_status: ExternalMessageStatus | None = None
    created_at: datetime
    updated_at: datetime


class EmailDraftSendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email_draft_id: UUID
    status: ExternalMessageStatus
    retryable: bool = False
