from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models import AIAnalysisStatus, AIFunctionType, AIResultLanguage, User
from backend.app.schemas.ai_history import AIHistoryPage
from backend.app.services.ai.history import AIHistoryDealNotFoundError, AIHistoryForbiddenError, list_ai_history, list_deal_ai_history


router = APIRouter(tags=["ai-history"])


def _filters(function_type, status, is_outdated, current_only, language, limit, offset):
    return dict(function_type=function_type, status=status, is_outdated=is_outdated, current_only=current_only, language=language, limit=limit, offset=offset)


@router.get("/ai-history", response_model=AIHistoryPage)
def get_global_ai_history(
    session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)],
    function_type: AIFunctionType | None = None, status: AIAnalysisStatus | None = None,
    deal_id: UUID | None = None, is_outdated: bool | None = None, current_only: bool = False,
    language: AIResultLanguage | None = None, limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return list_ai_history(session, current_user=current_user, deal_id=deal_id, **_filters(function_type, status, is_outdated, current_only, language, limit, offset))


@router.get("/deals/{deal_id}/ai-history", response_model=AIHistoryPage)
def get_deal_ai_history(
    deal_id: UUID, session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)],
    function_type: AIFunctionType | None = None, status: AIAnalysisStatus | None = None,
    is_outdated: bool | None = None, current_only: bool = False, language: AIResultLanguage | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0,
):
    try: return list_deal_ai_history(session, deal_id=deal_id, current_user=current_user, **_filters(function_type, status, is_outdated, current_only, language, limit, offset))
    except AIHistoryDealNotFoundError as error: raise HTTPException(404, "Deal not found") from error
    except AIHistoryForbiddenError as error: raise HTTPException(403, "AI History is available only for own Deals") from error
