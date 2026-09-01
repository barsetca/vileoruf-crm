from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


if TYPE_CHECKING:
    from backend.app.models.deal import Deal


WON_STAGE_NAME = "Won"
SYSTEM_PIPELINE: tuple[tuple[str, int], ...] = (
    ("New Lead", 1),
    ("Contact", 2),
    ("Qualification", 3),
    ("Proposal", 4),
    ("Negotiation", 5),
    (WON_STAGE_NAME, 6),
    ("Lost", 7),
)


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    deals: Mapped[list["Deal"]] = relationship(back_populates="stage")
