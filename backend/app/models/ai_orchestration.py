from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.ai import AIResultLanguage
from backend.app.models.user import utc_now


class InitialAIAnalysisPipeline(Base):
    """Correlation row for the one automatic AI pipeline of a newly created Deal."""

    __tablename__ = "initial_ai_analysis_pipelines"
    __table_args__ = (
        UniqueConstraint("deal_id"),
        Index("ix_initial_ai_analysis_pipelines_deal_id", "deal_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    deal_id: Mapped[UUID] = mapped_column(
        ForeignKey("deals.id"), nullable=False
    )
    language: Mapped[AIResultLanguage] = mapped_column(
        SqlEnum(AIResultLanguage, name="ai_result_language", create_type=False),
        nullable=False,
    )
    lead_scoring_analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_analyses.id"), nullable=False, unique=True
    )
    deal_prediction_analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_analyses.id"), nullable=False, unique=True
    )
    next_best_action_analysis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_analyses.id"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now,
        server_default=func.now(),
    )
