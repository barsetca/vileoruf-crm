from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import AIAnalysis, User
from backend.app.schemas.ai import (
    EmailDraftCreate,
    EmailDraftGenerationLaunch,
    EmailDraftResponse,
    EmailDraftUpdate,
    EmailGenerationOverview,
    EmailGenerationResponse,
)
from backend.app.services.ai.email_draft import (
    EmailDraftGenerationConfigurationError,
    EmailDraftGenerationDispatchError,
    EmailDraftGenerationForbiddenError,
    EmailDraftGenerationNotFoundError,
    InvalidSelectedNBAError,
    get_email_draft_overview,
    launch_email_draft,
    render_client_name,
)
from backend.app.services.ai.operations import AIOperationPersistenceError, DuplicateInFlightOperationError
from backend.app.services.ai.runtime_settings import AIIsDisabledError
from backend.app.api.ai.dependencies import require_manual_ai_launch_quota
from backend.app.services.email_drafts import (
    EmailDraftNotFoundError,
    EmailDraftPersistenceError,
    InvalidEmailDraftSourceError,
    create_email_draft,
    delete_email_draft,
    get_email_draft,
    list_email_drafts,
    update_email_draft,
)


generation_router = APIRouter(prefix="/deals/{deal_id}/email-draft", tags=["email-draft"])
draft_router = APIRouter(prefix="/deals/{deal_id}/email-drafts", tags=["email-drafts"])


def _render(analysis: AIAnalysis, client_name: str) -> dict:
    item = EmailGenerationResponse.model_validate(analysis).model_dump(mode="python")
    payload = item.get("result_payload")
    if payload:
        item["result_payload"] = {
            **payload,
            "subject": render_client_name(payload["subject"], client_name),
            "body": render_client_name(payload["body"], client_name),
        }
    return item


@generation_router.post("", response_model=EmailGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
def post_email_generation(deal_id: UUID, payload: EmailDraftGenerationLaunch, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], quota: Annotated[None, Depends(require_manual_ai_launch_quota)] = None):
    try:
        analysis = launch_email_draft(session, deal_id=deal_id, payload=payload, current_user=current_user)
        return _render(analysis, "")
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error
    except AIIsDisabledError as error: raise HTTPException(409, "AI is disabled by an administrator") from error
    except InvalidSelectedNBAError as error: raise HTTPException(422, "Selected Next Best Action is invalid for this Deal") from error
    except EmailDraftGenerationConfigurationError as error: raise HTTPException(422, "Email model configuration is invalid") from error
    except EmailDraftGenerationDispatchError as error: raise HTTPException(503, "Email Draft queue is unavailable") from error
    except DuplicateInFlightOperationError as error: raise HTTPException(409, "Email Draft generation is already running") from error
    except AIOperationPersistenceError as error: raise HTTPException(500, "Email Draft generation failed") from error


@generation_router.get("", response_model=EmailGenerationOverview)
def get_email_generation(deal_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], limit: Annotated[int, Query(ge=1, le=50)] = 20):
    try:
        deal, current, active, latest, history = get_email_draft_overview(session, deal_id=deal_id, current_user=current_user, limit=limit)
        return EmailGenerationOverview(current=_render(current, deal.client.name) if current else None, active=_render(active, deal.client.name) if active else None, latest_attempt=_render(latest, deal.client.name) if latest else None, history=[_render(item, deal.client.name) for item in history])
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error


@draft_router.get("", response_model=list[EmailDraftResponse])
def get_drafts(deal_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try: return list_email_drafts(session, deal_id=deal_id, current_user=current_user)
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error


@draft_router.post("", response_model=EmailDraftResponse, status_code=status.HTTP_201_CREATED)
def post_draft(deal_id: UUID, payload: EmailDraftCreate, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try: return create_email_draft(session, deal_id=deal_id, values=payload.model_dump(), current_user=current_user)
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error
    except InvalidEmailDraftSourceError as error: raise HTTPException(422, "Email generation source is invalid for this Deal") from error
    except EmailDraftPersistenceError as error: raise HTTPException(500, "Email Draft save failed") from error


@draft_router.get("/{draft_id}", response_model=EmailDraftResponse)
def get_draft(deal_id: UUID, draft_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try: return get_email_draft(session, deal_id=deal_id, draft_id=draft_id, current_user=current_user)
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error
    except EmailDraftNotFoundError as error: raise HTTPException(404, "Email Draft not found") from error


@draft_router.patch("/{draft_id}", response_model=EmailDraftResponse)
def patch_draft(deal_id: UUID, draft_id: UUID, payload: EmailDraftUpdate, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try: return update_email_draft(session, deal_id=deal_id, draft_id=draft_id, changes=payload.model_dump(exclude_unset=True), current_user=current_user)
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error
    except EmailDraftNotFoundError as error: raise HTTPException(404, "Email Draft not found") from error
    except EmailDraftPersistenceError as error: raise HTTPException(500, "Email Draft save failed") from error


@draft_router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(deal_id: UUID, draft_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    try:
        delete_email_draft(session, deal_id=deal_id, draft_id=draft_id, current_user=current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except EmailDraftGenerationNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except EmailDraftGenerationForbiddenError as error: raise HTTPException(403, "Email Draft is available only for own Deals") from error
    except EmailDraftNotFoundError as error: raise HTTPException(404, "Email Draft not found") from error
    except EmailDraftPersistenceError as error: raise HTTPException(500, "Email Draft delete failed") from error
