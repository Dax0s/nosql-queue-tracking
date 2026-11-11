"""Redis užraktai (`SET NX PX`), pvz. `lock:checkin:{user_id}:{queue_id}`."""

import secrets
from contextlib import asynccontextmanager

from app.db.redis import get_redis

# Atlaisvina tik tas, kas užrakino
_RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class LockNotAcquired(Exception):
    pass


@asynccontextmanager
async def redis_lock(key: str, ttl_ms: int = 3000):
    """`async with redis_lock(...)`: meta LockNotAcquired, jei užraktas užimtas."""
    r = get_redis()
    value = secrets.token_hex(8)
    if not await r.set(key, value, nx=True, px=ttl_ms):
        raise LockNotAcquired(key)
    try:
        yield
    finally:
        await r.eval(_RELEASE, 1, key, value)
