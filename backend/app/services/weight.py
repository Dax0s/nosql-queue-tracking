# Tiesinis blėsimas: svoris_dabar = max(0, weight − k · (dabar − weight_updated_at)),

from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from pymongo import ReturnDocument

from app.config import settings
from app.db.mongo import get_db
from app.db.redis import get_redis

WeightAction = Literal["create", "checkin", "review", "comment"]

_MS_PER_MIN = 60_000


def current_weight(doc: dict, now: datetime) -> float:
    """Dabartinis svoris iš eilės dokumento (reikia `weight`, `weight_updated_at`)."""
    minutes = (now - doc["weight_updated_at"]).total_seconds() / 60
    return max(0.0, doc["weight"] - settings.weight_decay_per_min * minutes)


def _update_pipeline(points: int, now: datetime) -> list[dict]:
    k = settings.weight_decay_per_min
    elapsed_min = {"$divide": [{"$subtract": [now, "$weight_updated_at"]}, _MS_PER_MIN]}
    decayed = {"$max": [0, {"$subtract": ["$weight", {"$multiply": [k, elapsed_min]}]}]}
    return [
        {
            "$set": {
                "weight": {"$min": [settings.weight_max, {"$add": [decayed, points]}]},
                "weight_updated_at": now,
            }
        },
        {
            "$set": {
                "expires_at": {
                    "$add": [now, {"$multiply": [{"$divide": ["$weight", k]}, _MS_PER_MIN]}]
                }
            }
        },
    ]


async def add_weight(queue_id: str, user_id: str, action: WeightAction) -> bool:
    if not ObjectId.is_valid(queue_id):
        return False

    r = get_redis()
    guard_key = f"weight:{queue_id}:{user_id}:{action}"
    if not await r.set(guard_key, 1, nx=True, ex=settings.weight_cooldown_sec):
        return False

    now = datetime.now(timezone.utc)
    try:
        doc = await get_db().queues.find_one_and_update(
            {"_id": ObjectId(queue_id)},
            _update_pipeline(settings.weight_points[action], now),
            projection={"expires_at": 1},
            return_document=ReturnDocument.AFTER,
        )
    except Exception:
        await r.delete(guard_key)
        raise

    if doc is None:
        await r.delete(guard_key)
        return False

    await r.expireat(f"queue:{queue_id}:active", doc["expires_at"])
    return True
