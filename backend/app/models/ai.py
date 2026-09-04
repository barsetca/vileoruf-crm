from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.deal import Deal
    from backend.app.models.email_draft import EmailDraft


class AIFunctionType(str, Enum):
    LEAD_SCORING = "LEAD_SCORING"
    DEAL_PREDICTION = "DEAL_PREDICTION"
    NEXT_BEST_ACTION = "NEXT_BEST_ACTION"
    EMAIL_DRAFT = "EMAIL_DRAFT"


class AIAnalysisStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AIResultLanguage(str, Enum):
    RU = "RU"
    EN = "EN"
    ES = "ES"


class AIErrorCategory(str, Enum):
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_STRUCTURED_RESPONSE = "INVALID_STRUCTURED_RESPONSE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 3",
            name="ck_ai_analyses_attempt_count_range",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_ai_analyses_duration_non_negative",
        ),
        CheckConstraint(
            "(status = 'QUEUED' AND started_at IS NULL) OR "
            "(status <> 'QUEUED' AND started_at IS NOT NULL)",
            name="ck_ai_analyses_started_lifecycle",
        ),
        CheckConstraint(
            "(status IN ('QUEUED', 'RUNNING') AND finished_at IS NULL "
            "AND duration_ms IS NULL AND result_payload IS NULL "
            "AND error_category IS NULL AND is_outdated = false) OR "
            "(status = 'SUCCESS' AND finished_at IS NOT NULL "
            "AND duration_ms IS NOT NULL AND result_payload IS NOT NULL "
            "AND error_category IS NULL) OR "
            "(status = 'FAILED' AND finished_at IS NOT NULL "
            "AND duration_ms IS NOT NULL AND result_payload IS NULL "
            "AND error_category IS NOT NULL AND is_outdated = false)",
            name="ck_ai_analyses_terminal_payload",
        ),
        Index(
            "uq_ai_analyses_deal_function_inflight",
            "deal_id",
            "function_type",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    deal_id: Mapped[UUID] = mapped_column(
        ForeignKey("deals.id"), nullable=False, index=True
    )
    function_type: Mapped[AIFunctionType] = mapped_column(
        SqlEnum(AIFunctionType, name="ai_function_type"), nullable=False
    )
    status: Mapped[AIAnalysisStatus] = mapped_column(
        SqlEnum(AIAnalysisStatus, name="ai_analysis_status"),
        nullable=False,
        default=AIAnalysisStatus.QUEUED,
        server_default=AIAnalysisStatus.QUEUED.value,
    )
    actual_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[AIResultLanguage] = mapped_column(
        SqlEnum(AIResultLanguage, name="ai_result_language"), nullable=False
    )
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_usage: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    error_category: Mapped[AIErrorCategory | None] = mapped_column(
        SqlEnum(AIErrorCategory, name="ai_error_category"), nullable=True
    )
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    is_outdated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    attempt_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

    deal: Mapped["Deal"] = relationship(back_populates="ai_analyses")
    email_drafts: Mapped[list["EmailDraft"]] = relationship(
        back_populates="source_ai_analysis"
    )
