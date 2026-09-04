from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.ai import AIAnalysisResponse, DealPredictionLaunch, DealPredictionOverview
from backend.app.services.ai.deal_prediction import ClosedDealPredictionError, DealPredictionConfigurationError, DealPredictionDispatchError, DealPredictionForbiddenError, DealPredictionNotFoundError, get_deal_prediction_overview, launch_deal_prediction
from backend.app.services.ai.operations import AIOperationPersistenceError, DuplicateInFlightOperationError
from backend.app.services.ai.runtime_settings import AIIsDisabledError
from backend.app.api.ai.dependencies import require_manual_ai_launch_quota

router = APIRouter(prefix="/deals/{deal_id}/deal-prediction", tags=["deal-prediction"])

@router.post("", response_model=AIAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
def post_prediction(deal_id: UUID, payload: DealPredictionLaunch, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], quota: Annotated[None, Depends(require_manual_ai_launch_quota)] = None):
    try: return launch_deal_prediction(session, deal_id=deal_id, language=payload.language, current_user=current_user)
    except DealPredictionNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except DealPredictionForbiddenError as error: raise HTTPException(403, "Deal Prediction is available only for own Deals") from error
    except ClosedDealPredictionError as error: raise HTTPException(409, "Closed Deals cannot start new Deal Prediction") from error
    except AIIsDisabledError as error: raise HTTPException(409, "AI is disabled by an administrator") from error
    except DealPredictionConfigurationError as error: raise HTTPException(422, "Deal Prediction configuration is incomplete") from error
    except DealPredictionDispatchError as error: raise HTTPException(503, "Deal Prediction queue is unavailable") from error
    except DuplicateInFlightOperationError as error: raise HTTPException(409, "Deal Prediction is already running") from error
    except AIOperationPersistenceError as error: raise HTTPException(500, "Deal Prediction operation failed") from error

@router.get("", response_model=DealPredictionOverview)
def get_prediction(deal_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], limit: Annotated[int, Query(ge=1, le=50)] = 20):
    try:
        current, active, latest, history = get_deal_prediction_overview(session, deal_id=deal_id, current_user=current_user, limit=limit)
        return DealPredictionOverview(current=current, active=active, latest_attempt=latest, history=history)
    except DealPredictionNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except DealPredictionForbiddenError as error: raise HTTPException(403, "Deal Prediction is available only for own Deals") from error
