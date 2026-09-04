import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import AIResultLanguage, Client, ClientStatus, Deal, PipelineStage, Service


WEBSITE_LEAD_SOURCE = "Website"
NEW_LEAD_STAGE_NAME = "New Lead"
logger = logging.getLogger(__name__)


class PublicRequestError(ValueError):
    pass


def create_public_request(
    session: Session,
    *,
    values: dict,
    analysis_language: AIResultLanguage | None = None,
) -> Deal:
    try:
        stage = session.scalar(select(PipelineStage).where(PipelineStage.name == NEW_LEAD_STAGE_NAME))
        if stage is None:
            raise PublicRequestError("Initial pipeline stage is not configured")
        deal_name = values.pop("deal_name")
        deal_values = {field: values.pop(field) for field in ("description", "estimated_budget", "deadline", "service_id")}
        service = session.get(Service, deal_values["service_id"])
        if service is None or not service.is_active or not service.category.is_active:
            raise PublicRequestError("Selected service is not available")
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
    except PublicRequestError:
        session.rollback()
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise PublicRequestError("Public request could not be saved") from error
    if analysis_language is not None:
        try:
            from backend.app.services.ai.orchestration import start_initial_ai_pipeline

            start_initial_ai_pipeline(
                session, deal_id=deal.id, language=analysis_language
            )
        except Exception:
            session.rollback()
            logger.error(
                "initial_ai_pipeline_start_failed deal=%s source=public", deal.id
            )
    return deal
