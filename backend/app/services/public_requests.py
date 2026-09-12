import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models import AIResultLanguage, Client, ClientStatus, Deal, PipelineStage, PublicRequest, Service
from backend.app.models.user import utc_now
from backend.app.core.identity import normalize_email
from backend.app.services.clients import find_client_by_email


WEBSITE_LEAD_SOURCE = "Website"
NEW_LEAD_STAGE_NAME = "New Lead"
# Update these constants only when the corresponding immutable legal PDF is replaced.
# The replacement procedure is documented in README and project status documentation.
PERSONAL_DATA_CONSENT_VERSION = "2026-09-10"
PRIVACY_POLICY_VERSION = "2026-09-10"
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
        request_values = dict(values)
        if request_values.pop("personal_data_consent", False) is not True:
            raise PublicRequestError("Personal-data consent is required")
        stage = session.scalar(select(PipelineStage).where(PipelineStage.name == NEW_LEAD_STAGE_NAME))
        if stage is None:
            raise PublicRequestError("Initial pipeline stage is not configured")
        deal_name = request_values.pop("deal_name")
        deal_values = {field: request_values.pop(field) for field in ("description", "estimated_budget", "deadline", "service_id")}
        service = session.get(Service, deal_values["service_id"])
        if service is None or not service.is_active or not service.category.is_active:
            raise PublicRequestError("Selected service is not available")
        consent_at = utc_now()
        client = find_client_by_email(session, request_values.get("email"))
        if client is None:
            client_values = dict(request_values)
            client_values["email"] = normalize_email(client_values.get("email"))
            client = Client(
                **client_values,
                lead_source=WEBSITE_LEAD_SOURCE,
                status=ClientStatus.CUSTOMER,
                personal_data_consent=True,
                personal_data_consent_at=consent_at,
                personal_data_consent_version=PERSONAL_DATA_CONSENT_VERSION,
                privacy_policy_version=PRIVACY_POLICY_VERSION,
            )
            session.add(client)
            session.flush()
        elif client.archived_at is not None:
            client.archived_at = None
        deal = Deal(
            client=client,
            stage_id=stage.id,
            responsible_user_id=None,
            name=deal_name,
            **deal_values,
        )
        snapshot = PublicRequest(
            client=client,
            deal=deal,
            name=request_values["name"],
            contact_person=request_values.get("contact_person"),
            email=request_values.get("email"),
            phone=request_values.get("phone"),
            telegram=request_values.get("telegram"),
            whatsapp=request_values.get("whatsapp"),
            company=request_values.get("company"),
            preferred_communication_language=request_values["preferred_communication_language"],
            deal_name=deal_name,
            description=deal_values["description"],
            service_id=service.id,
            service_name_ru=service.name_ru,
            service_name_en=service.name_en,
            service_name_es=service.name_es,
            estimated_budget=deal_values["estimated_budget"],
            deadline=deal_values["deadline"],
            personal_data_consent=True,
            personal_data_consent_at=consent_at,
            personal_data_consent_version=PERSONAL_DATA_CONSENT_VERSION,
            privacy_policy_version=PRIVACY_POLICY_VERSION,
        )
        session.add_all([deal, snapshot])
        session.commit()
    except PublicRequestError:
        session.rollback()
        raise
    except IntegrityError as error:
        # A concurrent public submission may have created the canonical Client
        # after our lookup. The unique index is authoritative; retry once using it.
        session.rollback()
        if find_client_by_email(session, values.get("email")) is not None:
            return create_public_request(session, values=values, analysis_language=analysis_language)
        raise PublicRequestError("Public request could not be saved") from error
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
