from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.user import utc_now


class AIModelSettings(Base):
    __tablename__ = "ai_model_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_ai_model_settings_singleton"),
        CheckConstraint(
            "deal_prediction_validity_days > 0",
            name="ck_ai_model_settings_prediction_validity_positive",
        ),
        CheckConstraint(
            "next_best_action_validity_days > 0",
            name="ck_ai_model_settings_nba_validity_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        SmallInteger, primary_key=True, default=1, server_default="1"
    )
    analysis_model_override: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    email_model_override: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    deal_prediction_validity_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=7, server_default="7"
    )
    next_best_action_validity_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=7, server_default="7"
    )
    ai_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    automatic_new_deal_analysis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
