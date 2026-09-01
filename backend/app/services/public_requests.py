from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import Client, ClientStatus, Deal, PipelineStage


WEBSITE_LEAD_SOURCE = "Website"
NEW_LEAD_STAGE_NAME = "New Lead"


class PublicRequestError(ValueError):
    pass


def create_public_request(session: Session, *, values: dict) -> Deal:
    try:
        stage = session.scalar(select(PipelineStage).where(PipelineStage.name == NEW_LEAD_STAGE_NAME))
        if stage is None:
            raise PublicRequestError("Initial pipeline stage is not configured")
        deal_name = values.pop("deal_name")
        deal_values = {field: values.pop(field) for field in ("description", "estimated_budget", "deadline")}
        client = Client(**values, lead_source=WEBSITE_LEAD_SOURCE, status=ClientStatus.CUSTOMER)
        deal = Deal(
            client=client,
            stage_id=stage.id,
            responsible_user_id=None,
            name=deal_name,
            **deal_values,
        )
        session.add(deal)
        session.commit()
        return deal
    except PublicRequestError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise PublicRequestError("Public request could not be saved") from error
