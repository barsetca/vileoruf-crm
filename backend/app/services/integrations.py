from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models import IntegrationConnection, IntegrationConnectionStatus, IntegrationProvider

DISPLAY_NAMES={IntegrationProvider.GMAIL:"Gmail",IntegrationProvider.TELEGRAM:"Telegram",IntegrationProvider.GOOGLE_CALENDAR:"Google Calendar",IntegrationProvider.WHATSAPP:"WhatsApp"}
def telegram_operational_available(session: Session) -> bool:
    connection=session.scalar(select(IntegrationConnection).where(IntegrationConnection.provider==IntegrationProvider.TELEGRAM))
    return connection is not None and connection.status is IntegrationConnectionStatus.CONNECTED
def list_integration_connections(session: Session):
    existing={item.provider:item for item in session.scalars(select(IntegrationConnection))}
    return [existing.get(provider) or {"provider":provider,"status":IntegrationConnectionStatus.DISCONNECTED,"display_name":DISPLAY_NAMES[provider]} for provider in IntegrationProvider]
