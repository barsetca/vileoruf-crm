import logging
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError

from backend.app.core.config import AIInfrastructureSettings, get_ai_infrastructure_settings


logger = logging.getLogger(__name__)
RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


@dataclass(frozen=True)
class AIRateLimitExceeded(Exception):
    retry_after_seconds: int


@lru_cache
def _redis_client(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)


def enforce_manual_ai_rate_limit(user_id: UUID, *, infrastructure: AIInfrastructureSettings | None = None, client: Redis | None = None) -> None:
    settings = infrastructure or get_ai_infrastructure_settings()
    redis_client = client or _redis_client(settings.celery_broker_url)
    key = f"vileoruf:ai-launch-rate:{user_id}"
    try:
        count, ttl = redis_client.eval(RATE_LIMIT_SCRIPT, 1, key, settings.ai_rate_limit_window_seconds)
    except RedisError:
        logger.warning("ai_rate_limit_unavailable actor=%s policy=fail_open", user_id)
        return
    if int(count) > settings.ai_rate_limit_requests:
        raise AIRateLimitExceeded(max(1, int(ttl)))
