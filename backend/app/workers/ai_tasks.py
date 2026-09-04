from backend.app.workers.celery_app import celery_app
from uuid import UUID

from backend.app.db.session import SessionLocal
from backend.app.models import AIAnalysis
from backend.app.services.ai.lead_scoring import execute_prepared_lead_scoring
from backend.app.services.ai.deal_prediction import execute_prepared_deal_prediction
from backend.app.services.ai.next_best_action import execute_prepared_next_best_action
from backend.app.services.ai.email_draft import execute_prepared_email_draft
from backend.app.services.ai.openai_provider import create_openai_provider


@celery_app.task(name="ai.foundation.ping")
def foundation_ping() -> dict[str, str]:
    """Infrastructure-only smoke task; real AI tasks arrive in D4.2-D4.5."""

    return {"status": "ok", "queue": "ai"}


@celery_app.task(name="ai.lead_scoring.execute")
def execute_lead_scoring(analysis_id: str, prepared_payload: dict) -> dict[str, str]:
    with SessionLocal() as session:
        analysis = session.get(AIAnalysis, UUID(analysis_id))
        if analysis is None:
            return {"status": "missing", "analysis_id": analysis_id}
        if analysis.status.value in ("SUCCESS", "FAILED"):
            from backend.app.services.ai.orchestration import advance_initial_ai_pipeline

            advance_initial_ai_pipeline(session, analysis_id=analysis.id)
            return {"status": analysis.status.value, "analysis_id": analysis_id}
        result = execute_prepared_lead_scoring(session, analysis=analysis, prepared_payload=prepared_payload, provider=create_openai_provider())
        from backend.app.services.ai.orchestration import advance_initial_ai_pipeline
        advance_initial_ai_pipeline(session, analysis_id=analysis.id)
        return {"status": result.status.value, "analysis_id": analysis_id}


@celery_app.task(name="ai.deal_prediction.execute")
def execute_deal_prediction(analysis_id: str, prepared_payload: dict) -> dict[str, str]:
    with SessionLocal() as session:
        analysis = session.get(AIAnalysis, UUID(analysis_id))
        if analysis is None:
            return {"status": "missing", "analysis_id": analysis_id}
        if analysis.status.value in ("SUCCESS", "FAILED"):
            from backend.app.services.ai.orchestration import advance_initial_ai_pipeline

            advance_initial_ai_pipeline(session, analysis_id=analysis.id)
            return {"status": analysis.status.value, "analysis_id": analysis_id}
        result = execute_prepared_deal_prediction(session, analysis=analysis, prepared_payload=prepared_payload, provider=create_openai_provider())
        from backend.app.services.ai.orchestration import advance_initial_ai_pipeline
        advance_initial_ai_pipeline(session, analysis_id=analysis.id)
        return {"status": result.status.value, "analysis_id": analysis_id}


@celery_app.task(name="ai.next_best_action.execute")
def execute_next_best_action(analysis_id: str, prepared_payload: dict) -> dict[str, str]:
    with SessionLocal() as session:
        analysis = session.get(AIAnalysis, UUID(analysis_id))
        if analysis is None:
            return {"status": "missing", "analysis_id": analysis_id}
        if analysis.status.value in ("SUCCESS", "FAILED"):
            from backend.app.services.ai.orchestration import advance_initial_ai_pipeline

            advance_initial_ai_pipeline(session, deal_id=analysis.deal_id)
            return {"status": analysis.status.value, "analysis_id": analysis_id}
        result = execute_prepared_next_best_action(
            session,
            analysis=analysis,
            prepared_payload=prepared_payload,
            provider=create_openai_provider(),
        )
        from backend.app.services.ai.orchestration import advance_initial_ai_pipeline
        advance_initial_ai_pipeline(session, deal_id=analysis.deal_id)
        return {"status": result.status.value, "analysis_id": analysis_id}


@celery_app.task(name="ai.email_draft.execute")
def execute_email_draft(analysis_id: str, prepared_payload: dict) -> dict[str, str]:
    with SessionLocal() as session:
        analysis = session.get(AIAnalysis, UUID(analysis_id))
        if analysis is None:
            return {"status": "missing", "analysis_id": analysis_id}
        if analysis.status.value in ("SUCCESS", "FAILED"):
            return {"status": analysis.status.value, "analysis_id": analysis_id}
        result = execute_prepared_email_draft(session, analysis=analysis, prepared_payload=prepared_payload, provider=create_openai_provider())
        return {"status": result.status.value, "analysis_id": analysis_id}
