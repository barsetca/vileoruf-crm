"""Employee-controlled EmailDraft CRUD.  It deliberately has no provider or Communication side effects."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from backend.app.models import AIAnalysis, AIAnalysisStatus, AIFunctionType, AIResultLanguage, Deal, EmailDraft, EmailDraftState, ExternalMessage, User, UserRole
from backend.app.services.ai.email_draft import EmailDraftGenerationForbiddenError, EmailDraftGenerationNotFoundError, _authorize, _load_deal


class EmailDraftNotFoundError(ValueError):
    pass


class EmailDraftPersistenceError(RuntimeError):
    pass


class InvalidEmailDraftSourceError(ValueError):
    pass

class SentEmailDraftImmutableError(ValueError):
    pass


def _source(session: Session, *, deal_id: UUID, source_id: UUID | None) -> AIAnalysis | None:
    if source_id is None:
        return None
    analysis = session.get(AIAnalysis, source_id)
    if analysis is None or analysis.deal_id != deal_id or analysis.function_type is not AIFunctionType.EMAIL_DRAFT or analysis.status is not AIAnalysisStatus.SUCCESS:
        raise InvalidEmailDraftSourceError
    return analysis


def list_email_drafts(session: Session, *, deal_id: UUID, current_user: User) -> list[EmailDraft]:
    deal = _load_deal(session, deal_id)
    _authorize(deal, current_user)
    drafts = list(session.scalars(select(EmailDraft).where(EmailDraft.deal_id == deal_id).order_by(EmailDraft.updated_at.desc(), EmailDraft.id.desc())))
    _attach_outbound_status(session, drafts)
    return drafts


def get_email_draft(session: Session, *, deal_id: UUID, draft_id: UUID, current_user: User) -> EmailDraft:
    deal = _load_deal(session, deal_id)
    _authorize(deal, current_user)
    draft = session.scalar(select(EmailDraft).where(EmailDraft.id == draft_id, EmailDraft.deal_id == deal_id))
    if draft is None:
        raise EmailDraftNotFoundError
    _attach_outbound_status(session, [draft])
    return draft


def _attach_outbound_status(session: Session, drafts: list[EmailDraft]) -> None:
    if not drafts:
        return
    statuses = dict(session.execute(select(ExternalMessage.email_draft_id, ExternalMessage.status).where(ExternalMessage.email_draft_id.in_([draft.id for draft in drafts]))).all())
    for draft in drafts:
        draft.outbound_status = statuses.get(draft.id)


def create_email_draft(session: Session, *, deal_id: UUID, values: dict, current_user: User) -> EmailDraft:
    deal = _load_deal(session, deal_id)
    _authorize(deal, current_user)
    _source(session, deal_id=deal_id, source_id=values.get("source_ai_analysis_id"))
    draft = EmailDraft(deal_id=deal_id, creator_user_id=current_user.id, language=values.get("language") or AIResultLanguage(deal.client.preferred_communication_language.value), subject=values["subject"], body=values["body"], purpose=values["purpose"], source_ai_analysis_id=values.get("source_ai_analysis_id"))
    session.add(draft)
    try:
        session.commit(); session.refresh(draft)
    except SQLAlchemyError as error:
        session.rollback(); raise EmailDraftPersistenceError from error
    return draft


def update_email_draft(session: Session, *, deal_id: UUID, draft_id: UUID, changes: dict, current_user: User) -> EmailDraft:
    draft = get_email_draft(session, deal_id=deal_id, draft_id=draft_id, current_user=current_user)
    if draft.state is EmailDraftState.SENT:
        raise SentEmailDraftImmutableError
    for field, value in changes.items():
        setattr(draft, field, value)
    try:
        session.commit(); session.refresh(draft)
    except SQLAlchemyError as error:
        session.rollback(); raise EmailDraftPersistenceError from error
    return draft


def delete_email_draft(session: Session, *, deal_id: UUID, draft_id: UUID, current_user: User) -> None:
    draft = get_email_draft(session, deal_id=deal_id, draft_id=draft_id, current_user=current_user)
    if draft.state is EmailDraftState.SENT:
        raise SentEmailDraftImmutableError
    try:
        session.delete(draft); session.commit()
    except SQLAlchemyError as error:
        session.rollback(); raise EmailDraftPersistenceError from error
