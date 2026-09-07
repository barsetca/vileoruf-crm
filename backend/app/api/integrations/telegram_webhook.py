from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_telegram_settings
from backend.app.db.session import get_db
from backend.app.services.telegram import TelegramError, process_telegram_update

router = APIRouter(prefix="/webhooks", tags=["telegram-webhook"])


@router.post("/telegram", include_in_schema=False)
async def telegram_webhook(request: Request, session: Annotated[Session, Depends(get_db)]):
    configured = get_telegram_settings().telegram_webhook_secret
    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if configured is None or not received or received != configured.get_secret_value():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Telegram webhook is not authorized")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid Telegram update") from None
    try:
        process_telegram_update(session, payload)
    except TelegramError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Telegram integration is unavailable") from None
    return {"ok": True}
