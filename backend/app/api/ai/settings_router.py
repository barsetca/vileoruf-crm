from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_admin
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.ai_settings import AISettingsResponse, AISettingsUpdate
from backend.app.services.ai.provider import ProviderFailure
from backend.app.services.ai.settings import AISettingsModelNotAllowedError, AISettingsPersistenceError, get_ai_settings, update_ai_settings


router = APIRouter(prefix="/settings/ai", tags=["ai-settings"])


@router.get("", response_model=AISettingsResponse)
def read_ai_settings(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    try: return get_ai_settings(session)
    except ProviderFailure as error: raise HTTPException(422, "AI model configuration is invalid") from error


@router.patch("", response_model=AISettingsResponse)
def patch_ai_settings(payload: AISettingsUpdate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]):
    try: return update_ai_settings(session, payload=payload, actor=admin)
    except AISettingsModelNotAllowedError as error: raise HTTPException(422, "Selected AI model is not allowed") from error
    except ProviderFailure as error: raise HTTPException(422, "AI model configuration is invalid") from error
    except AISettingsPersistenceError as error: raise HTTPException(500, "AI Settings update failed") from error
