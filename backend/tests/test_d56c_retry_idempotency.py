from backend.app.workers import integration_tasks
from backend.app.workers.celery_app import celery_app


def test_provider_tasks_use_integrations_queue_without_implicit_celery_autoretry():
    """Terminal lifecycle services decide retry safety; Celery must not replay them blindly."""
    tasks = (
        integration_tasks.send_gmail_external_message,
        integration_tasks.sync_gmail_inbound,
        integration_tasks.send_telegram_external_message,
        integration_tasks.create_google_calendar_event_task,
        integration_tasks.update_google_calendar_event_task,
    )

    for task in tasks:
        assert celery_app.conf.task_routes[task.name] == {"queue": "integrations"}
        assert getattr(task, "autoretry_for", None) is None
        assert getattr(task, "retry_kwargs", None) is None
