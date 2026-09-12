from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.services.gmail_outbound import execute_gmail_send
import logging
import time

from backend.app.services.gmail_inbound import GmailInboundError, execute_gmail_inbound_sync, get_usable_gmail_inbound_connection, request_gmail_inbound_sync
from backend.app.services.gmail_inbound_lock import GmailInboundSyncLockUnavailableError, acquire_gmail_inbound_sync_lock, release_gmail_inbound_sync_lock
from backend.app.services.telegram import execute_telegram_send
from backend.app.services.calendar_events import execute_calendar_event_create, execute_calendar_event_update
@celery_app.task(name="integrations.foundation.ping")
def foundation_ping(): return {"status":"ok","queue":"integrations"}


@celery_app.task(name="integrations.gmail.send")
def send_gmail_external_message(external_message_id: str):
    with SessionLocal() as session:
        message = execute_gmail_send(session, external_message_id=__import__("uuid").UUID(external_message_id))
        return {"external_message_id": str(message.id), "status": message.status.value}


logger = logging.getLogger(__name__)


@celery_app.task(name="integrations.gmail.periodic_dispatch")
def dispatch_periodic_gmail_inbound_sync():
    with SessionLocal() as session:
        try:
            connection = get_usable_gmail_inbound_connection(session)
        except GmailInboundError:
            logger.info("gmail_sync_trigger=periodic gmail_sync_status=skipped_unavailable")
            return {"dispatched": False, "reason": "unavailable"}
    sync_gmail_inbound.delay(trigger="periodic")
    logger.info("gmail_sync_trigger=periodic gmail_sync_status=scheduled integration_id=%s", connection.id)
    return {"dispatched": True}


@celery_app.task(name="integrations.gmail.inbound_sync")
def sync_gmail_inbound(trigger: str = "manual"):
    try:
        lock = acquire_gmail_inbound_sync_lock()
    except GmailInboundSyncLockUnavailableError:
        logger.warning("gmail_sync_trigger=%s gmail_sync_status=error reason=lock_unavailable", trigger)
        return {"skipped": "lock_unavailable"}
    if lock is None:
        logger.info("gmail_sync_trigger=%s gmail_sync_status=skipped_overlap", trigger)
        return {"skipped": "overlap"}

    started = time.monotonic()
    try:
        with SessionLocal() as session:
            try:
                connection = request_gmail_inbound_sync(session)
            except GmailInboundError:
                logger.info("gmail_sync_trigger=%s gmail_sync_status=skipped_unavailable", trigger)
                return {"skipped": "unavailable"}
            logger.info("gmail_sync_trigger=%s gmail_sync_status=start integration_id=%s", trigger, connection.id)
            result = execute_gmail_inbound_sync(session)
            duration_ms = int((time.monotonic() - started) * 1000)
            if "error" in result:
                logger.warning("gmail_sync_trigger=%s gmail_sync_status=error integration_id=%s duration_ms=%s error_code=%s", trigger, connection.id, duration_ms, result["error"])
            else:
                logger.info("gmail_sync_trigger=%s gmail_sync_status=success integration_id=%s duration_ms=%s", trigger, connection.id, duration_ms)
            return result
    finally:
        release_gmail_inbound_sync_lock(lock)


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
