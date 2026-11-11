"""Sesijos Redis: `session:{token}` -> Hash(user_id, role), TTL 24 h (pratęsiama)."""

import secrets

from app.config import settings
from app.db.redis import get_redis


def _key(token: str) -> str:
    return f"session:{token}"


async def create_session(user_id: str, role: str) -> str:
    token = secrets.token_urlsafe(32)
    r = get_redis()
    async with r.pipeline(transaction=True) as pipe:
        pipe.hset(_key(token), mapping={"user_id": user_id, "role": role})
        pipe.expire(_key(token), settings.session_ttl_sec)
        await pipe.execute()
    return token


async def get_session(token: str) -> dict | None:
    """Grąžina sesiją ir pratęsia jos TTL."""
    r = get_redis()
    data = await r.hgetall(_key(token))
    if not data:
        return None
    await r.expire(_key(token), settings.session_ttl_sec)
    return data


async def delete_session(token: str) -> None:
    await get_redis().delete(_key(token))
