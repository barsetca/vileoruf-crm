from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


if TYPE_CHECKING:
    from backend.app.models.client import Client
    from backend.app.models.deal import Deal
    from backend.app.models.user import User


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SqlEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.OPEN,
        server_default=TaskStatus.OPEN.value,
    )
    responsible_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    client_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("clients.id"), nullable=True, index=True
    )
    deal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("deals.id"), nullable=True, index=True
    )

    responsible_user: Mapped["User"] = relationship(
        back_populates="responsible_tasks"
    )
    client: Mapped["Client | None"] = relationship(back_populates="tasks")
    deal: Mapped["Deal | None"] = relationship(back_populates="tasks")
