from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user, require_admin
from backend.app.db.session import get_db
from backend.app.models import User
from backend.app.schemas.business import CategoryCreate, CategoryResponse, CategoryUpdate, LeadScoringSettingsPayload, LeadScoringSettingsResponse, ServiceCreate, ServiceResponse, ServiceUpdate
from backend.app.services.business import BusinessPersistenceError, BusinessRecordConflictError, BusinessRecordNotFoundError, InactiveCategoryError, create_category, create_service, get_lead_scoring_settings, list_categories, list_services, update_category, update_lead_scoring_settings, update_service


router = APIRouter(prefix="/business", tags=["business-configuration"])


@router.get("/categories", response_model=list[CategoryResponse])
def get_categories(session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]): return list_categories(session)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
def post_category(payload: CategoryCreate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]): return _handle(lambda: create_category(session, values=payload.model_dump(), actor=admin))


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def patch_category(category_id: UUID, payload: CategoryUpdate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]): return _handle(lambda: update_category(session, category_id=category_id, changes=payload.model_dump(exclude_unset=True), actor=admin))


@router.get("/services", response_model=list[ServiceResponse])
def get_services(session: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]): return list_services(session)


@router.post("/services", response_model=ServiceResponse, status_code=201)
def post_service(payload: ServiceCreate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]): return _handle(lambda: create_service(session, values=payload.model_dump(), actor=admin))


@router.patch("/services/{service_id}", response_model=ServiceResponse)
def patch_service(service_id: UUID, payload: ServiceUpdate, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]): return _handle(lambda: update_service(session, service_id=service_id, changes=payload.model_dump(exclude_unset=True), actor=admin))


@router.get("/lead-scoring-settings", response_model=LeadScoringSettingsResponse)
def get_settings(session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]): return get_lead_scoring_settings(session)


@router.put("/lead-scoring-settings", response_model=LeadScoringSettingsResponse)
def put_settings(payload: LeadScoringSettingsPayload, session: Annotated[Session, Depends(get_db)], admin: Annotated[User, Depends(require_admin)]): return _handle(lambda: update_lead_scoring_settings(session, payload=payload, actor=admin))


def _handle(operation):
    try: return operation()
    except BusinessRecordNotFoundError as error: raise HTTPException(404, "Business configuration record not found") from error
    except InactiveCategoryError as error: raise HTTPException(422, "Service category must be active") from error
    except BusinessRecordConflictError as error: raise HTTPException(409, "Localized Russian name must be unique") from error
    except BusinessPersistenceError as error: raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Business configuration operation failed") from error
