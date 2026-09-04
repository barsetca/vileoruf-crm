from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models import Category, Service


OTHER_CATEGORY_ID = UUID("d4200000-0000-4000-8000-000000000001")
GENERAL_SERVICE_ID = UUID("d4200000-0000-4000-8000-000000000002")


class BusinessCatalogBootstrapError(RuntimeError): pass


def bootstrap_business_catalog(session: Session) -> None:
    try:
        category = session.get(Category, OTHER_CATEGORY_ID)
        if category is None:
            name_conflict = session.scalar(select(Category.id).where(Category.name_ru == "Другое"))
            if name_conflict is not None:
                raise BusinessCatalogBootstrapError("Category 'Другое' already exists with another identifier")
            category = Category(id=OTHER_CATEGORY_ID, name_ru="Другое", name_en="Other", name_es="Otro", target_hourly_rate=Decimal("50.00"), target_effort=Decimal("8.00"), is_active=True)
            session.add(category)
        service = session.get(Service, GENERAL_SERVICE_ID)
        if service is None:
            name_conflict = session.scalar(select(Service.id).where(Service.name_ru == "Общий запрос"))
            if name_conflict is not None:
                raise BusinessCatalogBootstrapError("Service 'Общий запрос' already exists with another identifier")
            session.add(Service(id=GENERAL_SERVICE_ID, category_id=OTHER_CATEGORY_ID, name_ru="Общий запрос", name_en="General request", name_es="Solicitud general", is_active=True))
        session.commit()
    except BusinessCatalogBootstrapError:
        session.rollback(); raise
    except SQLAlchemyError as error:
        session.rollback(); raise BusinessCatalogBootstrapError("Business catalog bootstrap failed") from error


def main() -> int:
    with SessionLocal() as session:
        bootstrap_business_catalog(session)
    print("Business catalog bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
