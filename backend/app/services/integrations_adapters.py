import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from enum import Enum
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
class ProviderErrorCode(str,Enum): AUTH_REQUIRED="AUTH_REQUIRED"; INVALID_CONFIGURATION="INVALID_CONFIGURATION"; PERMISSION_DENIED="PERMISSION_DENIED"; INVALID_RECIPIENT="INVALID_RECIPIENT"; RATE_LIMITED="RATE_LIMITED"; PROVIDER_UNAVAILABLE="PROVIDER_UNAVAILABLE"; PROVIDER_ERROR="PROVIDER_ERROR"
class RetryClass(str,Enum): SAFE_RETRY="SAFE_RETRY"; NO_RETRY="NO_RETRY"; UNCERTAIN="UNCERTAIN"


GMAIL_SEND_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_MESSAGES_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
TELEGRAM_API_BASE = "https://api.telegram.org"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GOOGLE_CALENDAR_EVENTS_ENDPOINT = f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events"


@dataclass(frozen=True)
class GmailSendResult:
    provider_message_id: str
    provider_thread_id: str | None


class GmailAdapterError(ValueError):
    def __init__(self, code: ProviderErrorCode, retry_class: RetryClass):
        self.code = code
        self.retry_class = retry_class
        super().__init__(code.value)


def google_calendar_authorization_headers(*, access_token: str) -> dict[str, str]:
    """Keep Calendar-specific transport setup outside future business services/routes."""
    if not isinstance(access_token, str) or not access_token:
        raise GmailAdapterError(ProviderErrorCode.AUTH_REQUIRED, RetryClass.NO_RETRY)
    return {"Authorization": f"Bearer {access_token}"}


@dataclass(frozen=True)
class GoogleCalendarCreateResult:
    provider_event_id: str
    external_url: str | None


@dataclass(frozen=True)
class GoogleCalendarUpdateResult:
    external_url: str | None


def create_google_calendar_event(*, access_token: str, title: str, description: str | None, start_at: datetime, end_at: datetime, timezone_name: str) -> GoogleCalendarCreateResult:
    payload=_google_calendar_event_payload(title=title,description=description,start_at=start_at,end_at=end_at,timezone_name=timezone_name)
    try: response=httpx.post(GOOGLE_CALENDAR_EVENTS_ENDPOINT,json=payload,headers=google_calendar_authorization_headers(access_token=access_token),timeout=20.0)
    except httpx.RequestError as error: raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN) from error
    if response.status_code >= 500: raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN)
    if response.status_code == 429: raise GmailAdapterError(ProviderErrorCode.RATE_LIMITED,RetryClass.NO_RETRY)
    if response.status_code in {401,403}: raise GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED,RetryClass.NO_RETRY)
    if response.status_code >= 400: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.NO_RETRY)
    try: body=response.json(); event_id=body.get("id")
    except (ValueError,AttributeError) as error: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.UNCERTAIN) from error
    if not isinstance(event_id,str) or not event_id: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.UNCERTAIN)
    link=body.get("htmlLink")
    return GoogleCalendarCreateResult(provider_event_id=event_id,external_url=link if isinstance(link,str) else None)


def update_google_calendar_event(*, access_token: str, provider_event_id: str, title: str, description: str | None, start_at: datetime, end_at: datetime, timezone_name: str) -> GoogleCalendarUpdateResult:
    if not isinstance(provider_event_id,str) or not provider_event_id:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.NO_RETRY)
    try:
        response=httpx.patch(f"{GOOGLE_CALENDAR_EVENTS_ENDPOINT}/{quote(provider_event_id,safe='')}",json=_google_calendar_event_payload(title=title,description=description,start_at=start_at,end_at=end_at,timezone_name=timezone_name),headers=google_calendar_authorization_headers(access_token=access_token),timeout=20.0)
    except httpx.RequestError as error: raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN) from error
    if response.status_code >= 500: raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN)
    if response.status_code == 429: raise GmailAdapterError(ProviderErrorCode.RATE_LIMITED,RetryClass.NO_RETRY)
    if response.status_code in {401,403}: raise GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED,RetryClass.NO_RETRY)
    if response.status_code >= 400: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.NO_RETRY)
    try: body=response.json()
    except ValueError as error: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.UNCERTAIN) from error
    if not isinstance(body,dict): raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.UNCERTAIN)
    returned_id=body.get("id")
    if returned_id is not None and returned_id != provider_event_id: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.UNCERTAIN)
    link=body.get("htmlLink")
    return GoogleCalendarUpdateResult(external_url=link if isinstance(link,str) else None)


def cancel_google_calendar_event(*, access_token: str, provider_event_id: str) -> None:
    if not isinstance(provider_event_id,str) or not provider_event_id:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.NO_RETRY)
    try:
        response=httpx.delete(f"{GOOGLE_CALENDAR_EVENTS_ENDPOINT}/{quote(provider_event_id,safe='')}",headers=google_calendar_authorization_headers(access_token=access_token),timeout=20.0)
    except httpx.RequestError as error: raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN) from error
    if response.status_code >= 500: raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE,RetryClass.UNCERTAIN)
    if response.status_code == 429: raise GmailAdapterError(ProviderErrorCode.RATE_LIMITED,RetryClass.NO_RETRY)
    if response.status_code in {401,403}: raise GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED,RetryClass.NO_RETRY)
    if response.status_code >= 400: raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR,RetryClass.NO_RETRY)


def _google_calendar_event_payload(*, title: str, description: str | None, start_at: datetime, end_at: datetime, timezone_name: str) -> dict:
    event_timezone = ZoneInfo(timezone_name)
    payload={"summary": title, "start": {"dateTime": start_at.astimezone(event_timezone).isoformat(), "timeZone": timezone_name}, "end": {"dateTime": end_at.astimezone(event_timezone).isoformat(), "timeZone": timezone_name}}
    if description is not None: payload["description"] = description
    return payload


@dataclass(frozen=True)
class GmailMessagePage:
    message_ids: tuple[str, ...]
    next_page_token: str | None


@dataclass(frozen=True)
class GmailInboundMessage:
    provider_message_id: str
    provider_thread_id: str | None
    sender: str
    recipient: str
    subject: str
    content: str
    provider_created_at: datetime | None


@dataclass(frozen=True)
class TelegramSendResult:
    provider_message_id: str
    chat_id: str


def validate_telegram_bot(*, token: str) -> dict:
    payload = _telegram_post(token, "getMe", {})
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("id"), int):
        raise GmailAdapterError(ProviderErrorCode.INVALID_CONFIGURATION, RetryClass.NO_RETRY)
    return result


def send_telegram_message(*, token: str, chat_id: str, content: str) -> TelegramSendResult:
    payload = _telegram_post(token, "sendMessage", {"chat_id": chat_id, "text": content})
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("message_id"), int):
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.UNCERTAIN)
    return TelegramSendResult(provider_message_id=str(result["message_id"]), chat_id=str((result.get("chat") or {}).get("id", chat_id)))


def _telegram_post(token: str, method: str, data: dict) -> dict:
    try:
        response = httpx.post(f"{TELEGRAM_API_BASE}/bot{token}/{method}", json=data, timeout=20.0)
    except httpx.RequestError as error:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN) from error
    if response.status_code >= 500:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN)
    if response.status_code == 429:
        raise GmailAdapterError(ProviderErrorCode.RATE_LIMITED, RetryClass.NO_RETRY)
    try:
        payload = response.json()
    except ValueError as error:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.UNCERTAIN) from error
    if response.status_code in {401, 403} or not isinstance(payload, dict) or payload.get("ok") is not True:
        raise GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED, RetryClass.NO_RETRY)
    return payload


def send_gmail_message(*, access_token: str, recipient: str, subject: str, body: str) -> GmailSendResult:
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")
    try:
        response = httpx.post(
            GMAIL_SEND_ENDPOINT,
            json={"raw": encoded},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20.0,
        )
    except httpx.RequestError as error:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN) from error
    if response.status_code >= 500:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN)
    if response.status_code == 429:
        raise GmailAdapterError(ProviderErrorCode.RATE_LIMITED, RetryClass.NO_RETRY)
    if response.status_code in {401, 403}:
        raise GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED, RetryClass.NO_RETRY)
    if response.status_code == 400:
        raise GmailAdapterError(ProviderErrorCode.INVALID_RECIPIENT, RetryClass.NO_RETRY)
    if response.status_code >= 400:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    try:
        payload = response.json()
        message_id = payload.get("id")
        thread_id = payload.get("threadId")
    except (ValueError, AttributeError) as error:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.UNCERTAIN) from error
    if not isinstance(message_id, str) or not message_id:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.UNCERTAIN)
    return GmailSendResult(provider_message_id=message_id, provider_thread_id=thread_id if isinstance(thread_id, str) else None)


def list_gmail_inbound_message_ids(*, access_token: str, after: datetime, page_token: str | None, max_results: int = 25) -> GmailMessagePage:
    params = {"q": f"after:{int(after.timestamp())} -from:me", "maxResults": max_results}
    if page_token:
        params["pageToken"] = page_token
    payload = _gmail_get(access_token, GMAIL_MESSAGES_ENDPOINT, params=params)
    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    message_ids = tuple(item.get("id") for item in raw_messages if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"])
    if len(message_ids) != len(raw_messages):
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    token = payload.get("nextPageToken")
    return GmailMessagePage(message_ids=message_ids, next_page_token=token if isinstance(token, str) and token else None)


def get_gmail_inbound_message(*, access_token: str, provider_message_id: str) -> GmailInboundMessage:
    payload = _gmail_get(access_token, f"{GMAIL_MESSAGES_ENDPOINT}/{provider_message_id}", params={"format": "full"})
    return _parse_gmail_inbound_payload(payload)


def _gmail_get(access_token: str, url: str, *, params: dict) -> dict:
    try:
        response = httpx.get(url, params=params, headers={"Authorization": f"Bearer {access_token}"}, timeout=20.0)
    except httpx.RequestError as error:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN) from error
    if response.status_code >= 500:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_UNAVAILABLE, RetryClass.UNCERTAIN)
    if response.status_code == 429:
        raise GmailAdapterError(ProviderErrorCode.RATE_LIMITED, RetryClass.NO_RETRY)
    if response.status_code in {401, 403}:
        raise GmailAdapterError(ProviderErrorCode.PERMISSION_DENIED, RetryClass.NO_RETRY)
    if response.status_code >= 400:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    try:
        payload = response.json()
    except ValueError as error:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY) from error
    if not isinstance(payload, dict):
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    return payload


def _parse_gmail_inbound_payload(payload: dict) -> GmailInboundMessage:
    message_id = payload.get("id")
    thread_id = payload.get("threadId")
    raw_headers = (payload.get("payload") or {}).get("headers")
    if not isinstance(message_id, str) or not message_id or not isinstance(raw_headers, list):
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    headers = {item.get("name", "").lower(): item.get("value", "") for item in raw_headers if isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("value"), str)}
    sender = _normalized_address(headers.get("from", ""))
    recipient = _normalized_address(headers.get("to", ""), allow_empty=True) or "unknown"
    if not sender:
        raise GmailAdapterError(ProviderErrorCode.PROVIDER_ERROR, RetryClass.NO_RETRY)
    timestamp = None
    if headers.get("date"):
        try:
            timestamp = parsedate_to_datetime(headers["date"])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError, IndexError):
            timestamp = None
    content = _plain_content(payload.get("payload") or {})
    return GmailInboundMessage(provider_message_id=message_id, provider_thread_id=thread_id if isinstance(thread_id, str) else None, sender=sender, recipient=recipient, subject=headers.get("subject", ""), content=content, provider_created_at=timestamp)


def _normalized_address(value: str, *, allow_empty: bool = False) -> str | None:
    _name, address = parseaddr(value)
    if not address or address.count("@") != 1 or any(character.isspace() for character in address):
        return None if allow_empty else None
    local, domain = address.rsplit("@", 1)
    return address.lower() if local and "." in domain else None


def _plain_content(payload: dict) -> str:
    def decode(node: dict) -> str | None:
        data = (node.get("body") or {}).get("data")
        if not isinstance(data, str):
            return None
        try:
            return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace").strip()
        except (ValueError, UnicodeDecodeError):
            return None
    if payload.get("mimeType") == "text/plain":
        return decode(payload) or ""
    for part in payload.get("parts") or []:
        if isinstance(part, dict):
            value = _plain_content(part)
            if value:
                return value
    return ""
