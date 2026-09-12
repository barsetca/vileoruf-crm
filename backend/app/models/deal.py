from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.user import utc_now


if TYPE_CHECKING:
    from backend.app.models.ai import AIAnalysis
    from backend.app.models.client import Client
    from backend.app.models.communication import Communication
    from backend.app.models.pipeline_stage import PipelineStage
    from backend.app.models.task import Task
    from backend.app.models.email_draft import EmailDraft
    from backend.app.models.user import User
    from backend.app.models.business import Service
    from backend.app.models.public_request import PublicRequest


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint(
            "probability >= 0 AND probability <= 100",
            name="ck_deals_probability_range",
        ),
        CheckConstraint(
            "estimated_budget IS NULL OR estimated_budget >= 0",
            name="ck_deals_estimated_budget_non_negative",
        ),
        CheckConstraint(
            "manager_effort_estimate IS NULL OR manager_effort_estimate > 0",
            name="ck_deals_manager_effort_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    stage_id: Mapped[UUID] = mapped_column(
        ForeignKey("pipeline_stages.id"), nullable=False, index=True
    )
    probability: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id"), nullable=False, index=True
    )
    responsible_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    service_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("services.id"), nullable=True, index=True
    )
    manager_effort_estimate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    first_won_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )

    client: Mapped["Client"] = relationship(back_populates="deals")
    stage: Mapped["PipelineStage"] = relationship(back_populates="deals")
    responsible_user: Mapped["User | None"] = relationship(
        back_populates="responsible_deals"
    )
    communications: Mapped[list["Communication"]] = relationship(back_populates="deal")
    tasks: Mapped[list["Task"]] = relationship(back_populates="deal")
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(back_populates="deal")
    email_drafts: Mapped[list["EmailDraft"]] = relationship(back_populates="deal")
    service: Mapped["Service | None"] = relationship(back_populates="deals")
    public_request: Mapped["PublicRequest | None"] = relationship(back_populates="deal", uselist=False)
