from celery import Celery

from backend.app.core.config import get_ai_infrastructure_settings


settings = get_ai_infrastructure_settings()
celery_app = Celery(
    "vileoruf_crm_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.app.workers.ai_tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_serializer="json",
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
    task_routes={"ai.foundation.ping": {"queue": "ai"}, "ai.lead_scoring.execute": {"queue": "ai"}, "ai.deal_prediction.execute": {"queue": "ai"}, "ai.next_best_action.execute": {"queue": "ai"}, "ai.email_draft.execute": {"queue": "ai"}},
    task_serializer="json",
    task_track_started=True,
    timezone="UTC",
    worker_hijack_root_logger=False,
)
