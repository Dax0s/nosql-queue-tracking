"""Bendri Redis cache helperiai (JSON reikšmės su TTL). Raktai – spec. 8 skyrius."""

import json
from typing import Any

from app.db.redis import get_redis


async def cache_get(key: str) -> Any | None:
    raw = await get_redis().get(key)
    return json.loads(raw) if raw is not None else None


async def cache_set(key: str, value: Any, ttl_sec: int) -> None:
    await get_redis().set(key, json.dumps(value, default=str), ex=ttl_sec)


async def cache_delete(*keys: str) -> None:
    if keys:
        await get_redis().delete(*keys)


async def invalidate_queue(queue_id: str) -> None:
    """Trina eilės suvestinę ir pirmą komentarų puslapį."""
    await cache_delete(f"cache:queue:{queue_id}", f"cache:queue:{queue_id}:comments:1")
