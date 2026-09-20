from __future__ import annotations

import logging
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger("abhaysetu.redis")
_client: Optional[Redis] = None
_available = False


async def init_redis() -> None:
    global _client, _available
    settings = get_settings()
    try:
        _client = Redis.from_url(settings.redis_url, decode_responses=True)
        await _client.ping()
        _available = True
        logger.info("Redis reachable")
    except Exception as exc:  # noqa: BLE001
        _available = False
        logger.warning("Redis unavailable; continuing without it: %s", exc)
        if settings.redis_required:
            raise


async def close_redis() -> None:
    global _client, _available
    if _client is not None:
        await _client.close()
    _client = None
    _available = False


def redis_available() -> bool:
    return _available


async def redis_health() -> dict[str, Any]:
    if _client is None:
        return {"status": "unavailable", "detail": "Redis client not initialized"}
    try:
        await _client.ping()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "detail": str(exc)}


async def incr_with_ttl(key: str, ttl_seconds: int) -> int:
    if not _available or _client is None:
        return 0
    value = await _client.incr(key)
    if value == 1:
        await _client.expire(key, ttl_seconds)
    return int(value)


async def publish(channel: str, message: str) -> None:
    if _available and _client is not None:
        await _client.publish(channel, message)
