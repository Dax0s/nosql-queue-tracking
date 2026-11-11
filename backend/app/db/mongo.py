from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, GEOSPHERE

from app.config import settings

_client: AsyncIOMotorClient | None = None


def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_url, tz_aware=True)


def close() -> None:
    if _client is not None:
        _client.close()


def get_db() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB neprijungta")
    return _client[settings.mongo_db]


async def ping() -> bool:
    await get_db().command("ping")
    return True


async def ensure_indexes() -> None:
    """Indeksai pagal spec. 7 skyrių. Kviečiama startuojant, idempotentiška."""
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.queues.create_index([("location", GEOSPHERE), ("expires_at", ASCENDING)])
    await db.queues.create_index("created_by")
    await db.checkins.create_index([("user_id", ASCENDING), ("checked_in_at", DESCENDING)])
    await db.checkins.create_index(
        [("queue_id", ASCENDING), ("user_id", ASCENDING), ("checked_out_at", ASCENDING)]
    )
    await db.comments.create_index([("queue_id", ASCENDING), ("created_at", DESCENDING)])
    await db.comment_likes.create_index(
        [("comment_id", ASCENDING), ("user_id", ASCENDING)], unique=True
    )
    await db.reviews.create_index([("queue_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
