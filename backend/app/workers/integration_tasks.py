from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.services.gmail_outbound import execute_gmail_send
from backend.app.services.gmail_inbound import execute_gmail_inbound_sync
from backend.app.services.telegram import execute_telegram_send
from backend.app.services.calendar_events import execute_calendar_event_create, execute_calendar_event_update
@celery_app.task(name="integrations.foundation.ping")
def foundation_ping(): return {"status":"ok","queue":"integrations"}


@celery_app.task(name="integrations.gmail.send")
def send_gmail_external_message(external_message_id: str):
    with SessionLocal() as session:
        message = execute_gmail_send(session, external_message_id=__import__("uuid").UUID(external_message_id))
        return {"external_message_id": str(message.id), "status": message.status.value}


@celery_app.task(name="integrations.gmail.inbound_sync")
def sync_gmail_inbound():
    with SessionLocal() as session:
        return execute_gmail_inbound_sync(session)


@celery_app.task(name="integrations.telegram.send")
def send_telegram_external_message(external_message_id: str):
    with SessionLocal() as session:
        message=execute_telegram_send(session, external_message_id=__import__("uuid").UUID(external_message_id))
        return {"external_message_id": str(message.id), "status": message.status.value}

@celery_app.task(name="integrations.google_calendar.create")
def create_google_calendar_event_task(calendar_event_id: str):
    with SessionLocal() as session:
        event=execute_calendar_event_create(session,event_id=__import__("uuid").UUID(calendar_event_id))
        return {"calendar_event_id":str(event.id),"status":event.status.value}


@celery_app.task(name="integrations.google_calendar.update")
def update_google_calendar_event_task(calendar_event_id: str):
    with SessionLocal() as session:
        event=execute_calendar_event_update(session,event_id=__import__("uuid").UUID(calendar_event_id))
        return {"calendar_event_id":str(event.id),"status":event.status.value}
