import redis.asyncio as aioredis

from app.config import settings

_client: aioredis.Redis | None = None


def connect() -> None:
    global _client
    _client = aioredis.from_url(settings.redis_url, decode_responses=True)


async def close() -> None:
    if _client is not None:
        await _client.aclose()


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis neprijungta")
    return _client


async def ping() -> bool:
    return bool(await get_redis().ping())
