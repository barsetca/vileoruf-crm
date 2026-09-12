"""Bounded Redis single-flight protection for the one corporate Gmail inbox."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

import redis

from backend.app.core.config import get_ai_infrastructure_settings


GMAIL_INBOUND_SYNC_LOCK_KEY = "vileoruf:integrations:gmail:inbound-sync"
GMAIL_INBOUND_SYNC_LOCK_TTL_SECONDS = 600
_RELEASE_IF_OWNER = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"


class GmailInboundSyncLockUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GmailInboundSyncLock:
    client: redis.Redis
    token: str


def acquire_gmail_inbound_sync_lock() -> GmailInboundSyncLock | None:
    client = redis.Redis.from_url(get_ai_infrastructure_settings().celery_broker_url, decode_responses=True)
    token = secrets.token_urlsafe(24)
    try:
        acquired = client.set(
            GMAIL_INBOUND_SYNC_LOCK_KEY,
            token,
            nx=True,
            ex=GMAIL_INBOUND_SYNC_LOCK_TTL_SECONDS,
        )
    except redis.RedisError as error:
        client.close()
        raise GmailInboundSyncLockUnavailableError from error
    if not acquired:
        client.close()
        return None
    return GmailInboundSyncLock(client=client, token=token)


def release_gmail_inbound_sync_lock(lock: GmailInboundSyncLock) -> None:
    try:
        lock.client.eval(_RELEASE_IF_OWNER, 1, GMAIL_INBOUND_SYNC_LOCK_KEY, lock.token)
    except redis.RedisError:
        # The TTL is the safe recovery path when Redis is unavailable at release time.
        pass
    finally:
        lock.client.close()
