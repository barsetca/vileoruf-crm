from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.ai import AIResultLanguage
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.ai import AIAnalysis
    from backend.app.models.deal import Deal
    from backend.app.models.user import User


class EmailDraftState(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    deal_id: Mapped[UUID] = mapped_column(
        ForeignKey("deals.id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[AIResultLanguage] = mapped_column(
        SqlEnum(AIResultLanguage, name="ai_result_language"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    source_ai_analysis_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_analyses.id"), nullable=True, index=True
    )
    state: Mapped[EmailDraftState] = mapped_column(SqlEnum(EmailDraftState, name="email_draft_state"), nullable=False, default=EmailDraftState.DRAFT, server_default=EmailDraftState.DRAFT.value)
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

    deal: Mapped["Deal"] = relationship(back_populates="email_drafts")
    creator: Mapped["User"] = relationship(back_populates="email_drafts")
    source_ai_analysis: Mapped["AIAnalysis | None"] = relationship(
        back_populates="email_drafts"
    )
