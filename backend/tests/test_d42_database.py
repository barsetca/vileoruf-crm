import os
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.models import AIAnalysis, AIAnalysisStatus, AIErrorCategory, AIFunctionType, AIResultLanguage, Category, Client, Deal, PipelineStage, Service, User, UserRole
from backend.app.schemas.business import LeadScoringSettingsPayload
from backend.app.scripts.bootstrap_business_catalog import bootstrap_business_catalog
from backend.app.services.ai.lead_scoring import ClosedDealLeadScoringError, LeadScoringDispatchError, LeadScoringForbiddenError, _serialize_prepared, execute_prepared_lead_scoring, launch_lead_scoring, prepare_lead_scoring
from backend.app.services.ai.operations import DuplicateInFlightOperationError
from backend.app.services.ai.provider import ProviderResult
from backend.app.services.business import update_category, update_lead_scoring_settings, update_service
from backend.app.services.deals import transition_deal, update_deal


pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="Set RUN_DATABASE_TESTS=1 against PostgreSQL")


@pytest.fixture
def isolated_database() -> Iterator[tuple[URL, sessionmaker[Session]]]:
    source = make_url(get_settings().database_url)
    name = f"vileoruf_d42_{uuid4().hex}"
    maintenance = create_engine(source.set(database="postgres"), isolation_level="AUTOCOMMIT")
    isolated = source.set(database=name)
    engine = None
    with maintenance.connect() as connection: connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    from backend.app.core import config as config_module
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = isolated.render_as_string(False)
    config_module.get_settings.cache_clear()
    try:
        command.upgrade(Config("backend/alembic.ini"), "head")
        engine = create_engine(isolated)
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        yield isolated, factory
    finally:
        config_module.get_settings.cache_clear()
        if old is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = old
        if engine is not None: engine.dispose()
        with maintenance.connect() as connection: connection.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        maintenance.dispose()


def test_d42_migration_business_configuration_freshness_and_authorization(isolated_database, monkeypatch):
    url, factory = isolated_database
    engine = factory.kw["bind"]
    schema = inspect(engine)
    assert {"categories", "services", "lead_scoring_settings"}.issubset(schema.get_table_names())
    assert {"service_id", "manager_effort_estimate"}.issubset({column["name"] for column in schema.get_columns("deals")})
    assert "preferred_communication_language" in {column["name"] for column in schema.get_columns("clients")}

    with factory() as session:
        bootstrap_business_catalog(session); bootstrap_business_catalog(session)
        assert len(list(session.scalars(select(Category)))) == 1
        assert len(list(session.scalars(select(Service)))) == 1
        category = session.scalar(select(Category)); service = session.scalar(select(Service))
        admin = User(email="d42-admin@example.test", password_hash=hash_password("synthetic d42 admin password"), display_name="Admin", role=UserRole.ADMIN, is_active=True)
        manager = User(email="d42-manager@example.test", password_hash=hash_password("synthetic d42 manager password"), display_name="Manager", role=UserRole.MANAGER, is_active=True)
        other = User(email="d42-other@example.test", password_hash=hash_password("synthetic d42 other password"), display_name="Other", role=UserRole.MANAGER, is_active=True)
        active_stage = PipelineStage(name="New Lead", position=1); contact = PipelineStage(name="Contact", position=2); won = PipelineStage(name="Won", position=3)
        client = Client(name="Synthetic")
        session.add_all([admin, manager, other, active_stage, contact, won, client]); session.flush()
        deal = Deal(name="D4.2", description="brief", client_id=client.id, stage_id=active_stage.id, responsible_user_id=manager.id, service_id=service.id, estimated_budget=Decimal("400"))
        closed = Deal(name="Closed", client_id=client.id, stage_id=won.id, responsible_user_id=manager.id, service_id=service.id)
        session.add_all([deal, closed]); session.commit()

        prepared = prepare_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN)
        assert prepared.commercial.score == Decimal("70.0")
        assert set(prepared.provider_data) == {"service", "category", "deal_description", "desired_deadline", "recent_communications", "context_truncated"}
        assert prepared.provider_data["recent_communications"] == [] and prepared.provider_data["context_truncated"] is False
        assert all(key not in prepared.provider_data for key in ("client_name", "email", "phone", "company", "client_id", "user_id"))
        assert "Never calculate or return Commercial Value" in prepared.trusted_instructions

        with pytest.raises(LeadScoringForbiddenError): launch_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=other, dispatch=False)
        with pytest.raises(ClosedDealLeadScoringError): launch_lead_scoring(session, deal_id=closed.id, language=AIResultLanguage.EN, current_user=manager, dispatch=False)
        queued = launch_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=manager, dispatch=False)
        with pytest.raises(DuplicateInFlightOperationError): launch_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=admin, dispatch=False)
        queued.status = AIAnalysisStatus.FAILED; queued.started_at = datetime.now(timezone.utc); queued.finished_at = datetime.now(timezone.utc); queued.duration_ms = 0; queued.error_category = AIErrorCategory.CONFIGURATION_ERROR; session.commit()

        class FakeProvider:
            def generate_structured(self, request, response_model):
                assert request.untrusted_business_data == prepared.provider_data
                return ProviderResult(result={"service_fit":{"score":80,"explanation":"Service fits"},"lead_quality":{"score":60,"explanation":"Lead is usable"},"feasibility":{"score":90,"explanation":"Delivery is feasible"},"summary":"Validated fake result","missing_data_observations":[],"security_warning":"Suspicious instruction ignored","category_suggestion":None}, actual_model=request.model, usage={"total_tokens":42})

        executable = launch_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=admin, dispatch=False)
        completed = execute_prepared_lead_scoring(session, analysis=executable, prepared_payload=_serialize_prepared(prepared), provider=FakeProvider())
        assert completed.status is AIAnalysisStatus.SUCCESS
        assert completed.language is AIResultLanguage.EN
        assert completed.result_payload["commercial_value"]["score"] == "70.0"
        assert completed.result_payload["overall_score"] == "76.5"
        assert completed.result_payload["security_warning"] == "Suspicious instruction ignored"
        assert completed.id == executable.id and completed.attempt_count == 1

        success = AIAnalysis(deal_id=deal.id, function_type=AIFunctionType.LEAD_SCORING, status=AIAnalysisStatus.SUCCESS, language=AIResultLanguage.EN, prompt_version="test", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), duration_ms=1, input_fingerprint="a"*64, input_snapshot={}, result_payload={"overall_score":50}, is_outdated=False, attempt_count=1)
        closed_success = AIAnalysis(deal_id=closed.id, function_type=AIFunctionType.LEAD_SCORING, status=AIAnalysisStatus.SUCCESS, language=AIResultLanguage.EN, prompt_version="test", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), duration_ms=1, input_fingerprint="b"*64, input_snapshot={}, result_payload={"overall_score":50}, is_outdated=False, attempt_count=1)
        session.add_all([success, closed_success]); session.commit()
        transition_deal(session, deal_id=deal.id, stage_id=contact.id, current_user=manager)
        assert session.get(AIAnalysis, success.id).is_outdated is False
        update_deal(session, deal_id=deal.id, changes={"description":"changed"}, current_user=manager)
        assert session.get(AIAnalysis, success.id).is_outdated is True

        fresh = AIAnalysis(deal_id=deal.id, function_type=AIFunctionType.LEAD_SCORING, status=AIAnalysisStatus.SUCCESS, language=AIResultLanguage.EN, prompt_version="test", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), duration_ms=1, input_fingerprint="c"*64, input_snapshot={}, result_payload={"overall_score":60}, is_outdated=False, attempt_count=1)
        session.add(fresh); session.commit()
        update_category(session, category_id=category.id, changes={"target_hourly_rate":Decimal("55")}, actor=admin)
        assert session.get(AIAnalysis, fresh.id).is_outdated is True
        assert session.get(AIAnalysis, closed_success.id).is_outdated is False

        def successful(marker: str) -> AIAnalysis:
            item = AIAnalysis(deal_id=deal.id, function_type=AIFunctionType.LEAD_SCORING, status=AIAnalysisStatus.SUCCESS, language=AIResultLanguage.EN, prompt_version="test", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), duration_ms=1, input_fingerprint=marker*64, input_snapshot={}, result_payload={"overall_score":60}, is_outdated=False, attempt_count=1)
            session.add(item); session.commit(); return item

        for marker, changes in [
            ("e", {"estimated_budget":Decimal("500")}),
            ("f", {"deadline":date.today()+timedelta(days=30)}),
            ("g", {"manager_effort_estimate":Decimal("12")}),
        ]:
            item = successful(marker); update_deal(session, deal_id=deal.id, changes=changes, current_user=manager); assert session.get(AIAnalysis, item.id).is_outdated is True

        target_effort_analysis = successful("h")
        update_category(session, category_id=category.id, changes={"target_effort":Decimal("10")}, actor=admin)
        assert session.get(AIAnalysis, target_effort_analysis.id).is_outdated is True

        second_category = Category(name_ru="Видео", name_en="Video", name_es="Vídeo", target_hourly_rate=Decimal("60"), target_effort=Decimal("16"))
        second_service = Service(category=second_category, name_ru="Монтаж", name_en="Editing", name_es="Edición")
        session.add_all([second_category, second_service]); session.commit()
        service_analysis = successful("i")
        update_deal(session, deal_id=deal.id, changes={"service_id":second_service.id}, current_user=manager)
        assert session.get(AIAnalysis, service_analysis.id).is_outdated is True
        derived_analysis = successful("j")
        update_service(session, service_id=second_service.id, changes={"category_id":category.id}, actor=admin)
        assert session.get(AIAnalysis, derived_analysis.id).is_outdated is True

        latest = AIAnalysis(deal_id=deal.id, function_type=AIFunctionType.LEAD_SCORING, status=AIAnalysisStatus.SUCCESS, language=AIResultLanguage.EN, prompt_version="test", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), duration_ms=1, input_fingerprint="d"*64, input_snapshot={}, result_payload={"overall_score":70}, is_outdated=False, attempt_count=1)
        session.add(latest); session.commit()
        payload = LeadScoringSettingsPayload(service_fit_weight=25, commercial_value_weight=35, lead_quality_weight=15, feasibility_weight=25, commercial_value_scale=[{"ratio":"0.5","score":0},{"ratio":"1.5","score":100}])
        update_lead_scoring_settings(session, payload=payload, actor=admin)
        assert session.get(AIAnalysis, latest.id).is_outdated is True
        assert session.get(AIAnalysis, closed_success.id).is_outdated is False
        unchanged_settings = successful("k")
        update_lead_scoring_settings(session, payload=payload, actor=admin)
        assert session.get(AIAnalysis, unchanged_settings.id).is_outdated is False

        def broker_down(*args, **kwargs): raise RuntimeError("synthetic broker outage")
        monkeypatch.setattr("backend.app.workers.ai_tasks.execute_lead_scoring.delay", broker_down)
        with pytest.raises(LeadScoringDispatchError):
            launch_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=admin)
        failed_dispatch = session.scalar(select(AIAnalysis).where(AIAnalysis.deal_id == deal.id).order_by(AIAnalysis.created_at.desc(), AIAnalysis.id.desc()))
        assert failed_dispatch.status is AIAnalysisStatus.FAILED
        assert failed_dispatch.error_category is AIErrorCategory.PROVIDER_UNAVAILABLE

    old = os.environ.get("DATABASE_URL"); os.environ["DATABASE_URL"] = url.render_as_string(False); get_settings.cache_clear()
    try:
        command.downgrade(Config("backend/alembic.ini"), "20260902_0005")
        command.upgrade(Config("backend/alembic.ini"), "head")
    finally:
        get_settings.cache_clear()
        if old is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = old
