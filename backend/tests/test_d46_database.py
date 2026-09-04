import logging
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from backend.app.core.config import get_ai_infrastructure_settings
from backend.app.models import AIAnalysis, AIAnalysisStatus, AIErrorCategory, AIFunctionType, AIModelSettings, AIResultLanguage, EmailDraft
from backend.app.schemas.ai import EmailDraftGenerationLaunch
from backend.app.schemas.ai_settings import AISettingsUpdate
from backend.app.services.ai.deal_prediction import get_deal_prediction_overview, launch_deal_prediction, prepare_deal_prediction
from backend.app.services.ai.email_draft import launch_email_draft, prepare_email_draft
from backend.app.services.ai.history import AIHistoryForbiddenError, list_ai_history, list_deal_ai_history
from backend.app.services.ai.lead_scoring import launch_lead_scoring, prepare_lead_scoring
from backend.app.services.ai.next_best_action import get_next_best_action_overview, launch_next_best_action, prepare_next_best_action
from backend.app.services.ai.runtime_settings import AIIsDisabledError
from backend.app.services.ai.settings import AISettingsModelNotAllowedError, get_ai_settings, update_ai_settings
from backend.app.services.email_drafts import create_email_draft
from backend.tests.test_d44_database import _seed, _success, isolated_database


pytestmark = pytest.mark.skipif(os.getenv("RUN_DATABASE_TESTS") != "1", reason="Set RUN_DATABASE_TESTS=1 against PostgreSQL")


def _lead_result():
    factor = {"score":"70.0","explanation":"Safe explanation"}
    return {"overall_score":"70.0","service_fit":factor,"commercial_value":{**factor,"status":"CALCULATED","effective_effort":"8","deal_hourly_rate":"100","ratio":"2"},"lead_quality":factor,"feasibility":factor,"summary":"Summary","missing_data":[],"security_warning":None,"category_suggestion":None}


def _dp_result(): return {"probability_won":60,"confidence":"MEDIUM","summary":"Summary","positive_signals":[],"risks":[],"missing_context":[],"security_warning":None}
def _nba_result(): return {"actions":[{"rank":1,"priority":"HIGH","action":"Follow up","reason":"Recent request","timing":"Today"}],"summary":"Summary","security_warning":None}
def _email_result(): return {"subject":"Hello {{client_name}}","body":"Body","security_warning":None}


def _failed(session, deal):
    now = datetime.now(timezone.utc)
    item = AIAnalysis(deal_id=deal.id,function_type=AIFunctionType.LEAD_SCORING,status=AIAnalysisStatus.FAILED,language=AIResultLanguage.EN,prompt_version="test",started_at=now,finished_at=now,duration_ms=1,input_fingerprint="f"*64,input_snapshot={},error_category=AIErrorCategory.PROVIDER_UNAVAILABLE,attempt_count=1)
    session.add(item); session.commit(); return item


def test_ai_settings_allowlist_reset_atomicity_routing_and_audit(isolated_database, caplog):
    with isolated_database() as session:
        admin, _, _, _, _, _, _, deal, _ = _seed(session)
        initial = get_ai_settings(session)
        assert initial.effective_analysis_model == initial.default_analysis_model
        assert not any(secret in initial.model_dump() for secret in ("openai_api_key", "celery_broker_url", "jwt_secret_key"))
        allowed = initial.allowed_models
        analysis_override = allowed[1]; email_override = allowed[-1]
        logging.getLogger("backend.app.services.ai.settings").disabled = False
        with caplog.at_level(logging.INFO, logger="backend.app.services.ai.settings"):
            changed = update_ai_settings(session, payload=AISettingsUpdate(analysis_model_override=analysis_override,email_model_override=email_override,deal_prediction_validity_days=14,next_best_action_validity_days=21,automatic_new_deal_analysis=False), actor=admin)
        assert changed.effective_analysis_model == analysis_override and changed.effective_email_model == email_override
        assert "actor=" in caplog.text and "analysis_model_override" in caplog.text and "email_model_override" in caplog.text
        assert "OPENAI_API_KEY" not in caplog.text and "redis://" not in caplog.text
        lead = prepare_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN)
        prepared = prepare_deal_prediction(session, deal_id=deal.id, language=AIResultLanguage.EN)
        nba = prepare_next_best_action(session, deal_id=deal.id, language=AIResultLanguage.EN)
        email = prepare_email_draft(session, deal_id=deal.id, payload=EmailDraftGenerationLaunch(purpose="Follow up"))
        assert lead.model == prepared.model == nba.model == analysis_override
        assert email.model == email_override
        next_analysis_model = allowed[0]
        update_ai_settings(session, payload=AISettingsUpdate(analysis_model_override=next_analysis_model), actor=admin)
        assert prepared.model == analysis_override
        assert prepare_deal_prediction(session, deal_id=deal.id, language=AIResultLanguage.EN).model == next_analysis_model
        assert prepare_email_draft(session, deal_id=deal.id, payload=EmailDraftGenerationLaunch(purpose="Follow up")).model == email_override
        before = get_ai_settings(session)
        caplog.clear()
        with pytest.raises(AISettingsModelNotAllowedError): update_ai_settings(session, payload=AISettingsUpdate(ai_enabled=False,analysis_model_override="not-allowed"), actor=admin)
        after = get_ai_settings(session)
        assert after.ai_enabled == before.ai_enabled and after.analysis_model_override == before.analysis_model_override
        assert "ai_setting_changed" not in caplog.text
        reset = update_ai_settings(session, payload=AISettingsUpdate(analysis_model_override=None,email_model_override=None), actor=admin)
        assert reset.effective_analysis_model == reset.default_analysis_model and reset.effective_email_model == reset.default_email_model


def test_unified_history_authorization_filters_current_and_safe_results(isolated_database):
    with isolated_database() as session:
        admin, manager, other, _, _, client, _, deal, closed = _seed(session)
        closed.responsible_user_id = other.id; session.commit()
        successful = [
            _success(session, deal, AIFunctionType.LEAD_SCORING, _lead_result(), "a"),
            _success(session, deal, AIFunctionType.DEAL_PREDICTION, _dp_result(), "b"),
            _success(session, deal, AIFunctionType.NEXT_BEST_ACTION, _nba_result(), "c", outdated=True),
            _success(session, deal, AIFunctionType.EMAIL_DRAFT, _email_result(), "d"),
            _success(session, closed, AIFunctionType.DEAL_PREDICTION, _dp_result(), "e"),
        ]
        failure = _failed(session, deal)
        admin_page = list_ai_history(session, current_user=admin, limit=100)
        assert admin_page.total == 6 and {item.function_type for item in admin_page.items} == set(AIFunctionType)
        manager_page = list_ai_history(session, current_user=manager, limit=100)
        assert manager_page.total == 5 and all(item.deal_id == deal.id for item in manager_page.items)
        assert failure.id in {item.id for item in manager_page.items}
        first_page = list_ai_history(session, current_user=manager, limit=2, offset=0)
        second_page = list_ai_history(session, current_user=manager, limit=2, offset=2)
        assert first_page.total == second_page.total == 5
        assert not ({item.id for item in first_page.items} & {item.id for item in second_page.items})
        assert first_page.items == sorted(first_page.items, key=lambda item: (item.created_at, item.id), reverse=True)
        failed_only = list_ai_history(session, current_user=manager, status=AIAnalysisStatus.FAILED)
        assert failed_only.total == 1 and failed_only.items[0].result_payload is None
        lead_current = list_ai_history(session, current_user=manager, function_type=AIFunctionType.LEAD_SCORING, current_only=True)
        assert lead_current.total == 1 and lead_current.items[0].id == successful[0].id
        outdated = list_ai_history(session, current_user=manager, is_outdated=True)
        assert outdated.total == 1 and outdated.items[0].function_type is AIFunctionType.NEXT_BEST_ACTION
        email = next(item for item in manager_page.items if item.function_type is AIFunctionType.EMAIL_DRAFT)
        assert client.name in email.result_payload.subject and "{{client_name}}" not in email.result_payload.subject
        assert not hasattr(email, "input_fingerprint") and not hasattr(email, "input_snapshot")
        with pytest.raises(AIHistoryForbiddenError): list_deal_ai_history(session, deal_id=closed.id, current_user=manager)
        hidden_filter = list_ai_history(session, current_user=manager, deal_id=closed.id)
        assert hidden_filter.total == 0 and hidden_filter.items == []


def test_history_handles_all_technical_states_and_malformed_success_safely(isolated_database):
    with isolated_database() as session:
        admin, _, _, _, _, _, _, deal, _ = _seed(session)
        now = datetime.now(timezone.utc)
        queued = AIAnalysis(deal_id=deal.id,function_type=AIFunctionType.DEAL_PREDICTION,status=AIAnalysisStatus.QUEUED,language=AIResultLanguage.RU,prompt_version="test",input_fingerprint="q"*64,input_snapshot={"private":"not returned"},attempt_count=0)
        running = AIAnalysis(deal_id=deal.id,function_type=AIFunctionType.NEXT_BEST_ACTION,status=AIAnalysisStatus.RUNNING,language=AIResultLanguage.ES,prompt_version="test",started_at=now,input_fingerprint="r"*64,input_snapshot={},attempt_count=1)
        malformed = AIAnalysis(deal_id=deal.id,function_type=AIFunctionType.EMAIL_DRAFT,status=AIAnalysisStatus.SUCCESS,language=AIResultLanguage.EN,prompt_version="test",started_at=now,finished_at=now,duration_ms=2,input_fingerprint="m"*64,input_snapshot={},result_payload={"raw":"unsafe shape"},provider_usage={"total_tokens":9,"raw_provider":"hidden"},attempt_count=1)
        session.add_all([queued, running, malformed]); session.commit()
        page = list_ai_history(session, current_user=admin, limit=100)
        by_id = {item.id:item for item in page.items}
        assert by_id[queued.id].status is AIAnalysisStatus.QUEUED and by_id[queued.id].result_payload is None
        assert by_id[running.id].status is AIAnalysisStatus.RUNNING and by_id[running.id].result_payload is None
        assert by_id[malformed.id].result_valid is False and by_id[malformed.id].result_payload is None
        assert by_id[malformed.id].provider_usage.total_tokens == 9
        assert "raw_provider" not in by_id[malformed.id].provider_usage.model_dump()
        assert not hasattr(by_id[malformed.id], "input_snapshot") and not hasattr(by_id[malformed.id], "input_fingerprint")


def test_settings_validity_changes_drive_lazy_history_freshness_only(isolated_database):
    with isolated_database() as session:
        admin, _, _, _, _, _, _, deal, closed = _seed(session)
        old = datetime.now(timezone.utc) - timedelta(days=10)
        active_dp = _success(session, deal, AIFunctionType.DEAL_PREDICTION, _dp_result(), "v")
        active_nba = _success(session, deal, AIFunctionType.NEXT_BEST_ACTION, _nba_result(), "w")
        closed_dp = _success(session, closed, AIFunctionType.DEAL_PREDICTION, _dp_result(), "x")
        lead = _success(session, deal, AIFunctionType.LEAD_SCORING, _lead_result(), "y")
        email = _success(session, deal, AIFunctionType.EMAIL_DRAFT, _email_result(), "z")
        for item in (active_dp, active_nba, closed_dp, lead, email): item.finished_at = old
        session.commit()
        update_ai_settings(session, payload=AISettingsUpdate(deal_prediction_validity_days=20,next_best_action_validity_days=20), actor=admin)
        before_count = session.scalar(select(func.count()).select_from(AIAnalysis))
        list_ai_history(session, current_user=admin, limit=100)
        assert active_dp.is_outdated is active_nba.is_outdated is False
        update_ai_settings(session, payload=AISettingsUpdate(deal_prediction_validity_days=5,next_best_action_validity_days=5), actor=admin)
        outdated = list_ai_history(session, current_user=admin, is_outdated=True, limit=100)
        session.refresh(active_dp); session.refresh(active_nba); session.refresh(closed_dp); session.refresh(lead); session.refresh(email)
        assert {active_dp.id, active_nba.id}.issubset({item.id for item in outdated.items})
        assert active_dp.is_outdated and active_nba.is_outdated
        assert not closed_dp.is_outdated and not lead.is_outdated and not email.is_outdated
        assert session.scalar(select(func.count()).select_from(AIAnalysis)) == before_count


def test_ai_disabled_blocks_all_generation_but_not_history_or_manual_drafts(isolated_database):
    with isolated_database() as session:
        admin, manager, _, _, _, _, _, deal, _ = _seed(session)
        session.add(AIModelSettings(id=1, ai_enabled=False, automatic_new_deal_analysis=True, deal_prediction_validity_days=7, next_best_action_validity_days=7))
        session.commit()
        before = session.scalar(select(func.count()).select_from(AIAnalysis))
        with pytest.raises(AIIsDisabledError): launch_lead_scoring(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=manager, dispatch=False)
        with pytest.raises(AIIsDisabledError): launch_deal_prediction(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=manager, dispatch=False)
        with pytest.raises(AIIsDisabledError): launch_next_best_action(session, deal_id=deal.id, language=AIResultLanguage.EN, current_user=manager, dispatch=False)
        with pytest.raises(AIIsDisabledError): launch_email_draft(session, deal_id=deal.id, payload=EmailDraftGenerationLaunch(purpose="Follow up"), current_user=manager, dispatch=False)
        assert session.scalar(select(func.count()).select_from(AIAnalysis)) == before
        assert list_ai_history(session, current_user=admin).total == 0
        draft = create_email_draft(session, deal_id=deal.id, current_user=manager, values={"subject":"Manual","body":"Still available","purpose":"Follow up","language":AIResultLanguage.EN,"source_ai_analysis_id":None})
        assert session.get(EmailDraft, draft.id) is not None
