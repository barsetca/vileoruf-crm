from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.ai import (
    AIAnalysisResponse,
    NextBestActionLaunch,
    NextBestActionOverview,
)
from backend.app.services.ai.next_best_action import (
    ClosedDealNextBestActionError,
    NextBestActionConfigurationError,
    NextBestActionDispatchError,
    NextBestActionForbiddenError,
    NextBestActionNotFoundError,
    get_next_best_action_overview,
    launch_next_best_action,
)
from backend.app.services.ai.operations import (
    AIOperationPersistenceError,
    DuplicateInFlightOperationError,
)
from backend.app.services.ai.runtime_settings import AIIsDisabledError
from backend.app.api.ai.dependencies import require_manual_ai_launch_quota


router = APIRouter(
    prefix="/deals/{deal_id}/next-best-action", tags=["next-best-action"]
)


@router.post(
    "", response_model=AIAnalysisResponse, status_code=status.HTTP_202_ACCEPTED
)
def post_next_best_action(
    deal_id: UUID,
    payload: NextBestActionLaunch,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    quota: Annotated[None, Depends(require_manual_ai_launch_quota)] = None,
):
    try:
        return launch_next_best_action(
            session,
            deal_id=deal_id,
            language=payload.language,
            current_user=current_user,
        )
    except NextBestActionNotFoundError as error:
        raise HTTPException(404, "Deal not found") from error
    except NextBestActionForbiddenError as error:
        raise HTTPException(403, "Next Best Action is available only for own Deals") from error
    except ClosedDealNextBestActionError as error:
        raise HTTPException(409, "Closed Deals cannot start new Next Best Action") from error
    except AIIsDisabledError as error:
        raise HTTPException(409, "AI is disabled by an administrator") from error
    except NextBestActionConfigurationError as error:
        raise HTTPException(422, "Next Best Action configuration is incomplete") from error
    except NextBestActionDispatchError as error:
        raise HTTPException(503, "Next Best Action queue is unavailable") from error
    except DuplicateInFlightOperationError as error:
        raise HTTPException(409, "Next Best Action is already running") from error
    except AIOperationPersistenceError as error:
        raise HTTPException(500, "Next Best Action operation failed") from error


@router.get("", response_model=NextBestActionOverview)
def get_next_best_action(
    deal_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    try:
        current, active, latest, history, waiting = get_next_best_action_overview(
            session, deal_id=deal_id, current_user=current_user, limit=limit
        )
        return NextBestActionOverview(
            current=current,
            active=active,
            latest_attempt=latest,
            history=history,
            waiting_for_initial_analyses=waiting,
        )
    except NextBestActionNotFoundError as error:
        raise HTTPException(404, "Deal not found") from error
    except NextBestActionForbiddenError as error:
        raise HTTPException(403, "Next Best Action is available only for own Deals") from error
