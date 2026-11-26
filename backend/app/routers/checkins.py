"""Check-in / check-out (eiga – spec. 8 skyrius). Atsakingas: žmogus A."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pymongo import DESCENDING, ReturnDocument

from app.auth.deps import UserOnly
from app.db.mongo import get_db
from app.db.redis import get_redis
from app.models.schemas import CheckinOut, CheckoutOut
from app.services.cache import invalidate_queue
from app.services.events import track_event
from app.services.locks import LockNotAcquired, redis_lock
from app.services.weight import add_weight

router = APIRouter(prefix="/queues", tags=["Check-in"])


def _active_key(queue_id: str) -> str:
    return f"queue:{queue_id}:active"


@router.post(
    "/{queue_id}/checkin",
    response_model=CheckinOut,
    status_code=status.HTTP_201_CREATED,
    summary="Pasižymėti eilėje",
    responses={
        404: {"description": "Eilė nerasta"},
        409: {
            "description": "Jau pasižymėjęs arba jau stovėjęs šioje eilėje, "
            "eilė nebeaktyvi arba užklausa jau vykdoma"
        },
    },
)
async def checkin(queue_id: str, user: UserOnly):
    if not ObjectId.is_valid(queue_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Eilė nerasta")

    try:
        async with redis_lock(f"lock:checkin:{user.user_id}:{queue_id}"):
            return await _do_checkin(queue_id, user.user_id)
    except LockNotAcquired:
        raise HTTPException(status.HTTP_409_CONFLICT, "Check-in jau vykdomas")


async def _do_checkin(queue_id: str, user_id: str) -> CheckinOut:
    db = get_db()
    r = get_redis()
    qid = ObjectId(queue_id)
    now = datetime.now(timezone.utc)

    queue = await db.queues.find_one({"_id": qid}, {"title": 1, "expires_at": 1})
    if queue is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Eilė nerasta")
    if queue["expires_at"] <= now:
        raise HTTPException(status.HTTP_409_CONFLICT, "Eilė nebeaktyvi")

    active_key = _active_key(queue_id)
    if await r.sismember(active_key, user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Jau esi pasižymėjęs šioje eilėje")

    if await db.checkins.find_one({"queue_id": qid, "user_id": ObjectId(user_id)}, {"_id": 1}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Šioje eilėje jau stovėjai")

    await db.checkins.insert_one(
        {
            "queue_id": qid,
            "user_id": ObjectId(user_id),
            "queue_title": queue["title"],
            "checked_in_at": now,
            "checked_out_at": None,
        }
    )

    # Rinkinys gyvuoja iki eilės expires_at. Naujam raktui (be TTL) EXPIREAT GT netinka,
    # todėl NX nustato TTL naujam raktui, o GT tik pratęsia esamą.
    async with r.pipeline(transaction=True) as pipe:
        pipe.sadd(active_key, user_id)
        pipe.expireat(active_key, queue["expires_at"], nx=True)
        pipe.expireat(active_key, queue["expires_at"], gt=True)
        pipe.scard(active_key)
        *_, active_count = await pipe.execute()

    await add_weight(queue_id, user_id, "checkin")
    await invalidate_queue(queue_id)
    await track_event("checkin", user_id=user_id, queue_id=queue_id)

    return CheckinOut(queue_id=queue_id, checked_in_at=now, active_count=active_count)


@router.post(
    "/{queue_id}/checkout",
    response_model=CheckoutOut,
    summary="Išeiti iš eilės",
    responses={
        404: {"description": "Eilė nerasta"},
        409: {"description": "Vartotojas nėra pasižymėjęs šioje eilėje"},
    },
)
async def checkout(queue_id: str, user: UserOnly):
    if not ObjectId.is_valid(queue_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Eilė nerasta")

    r = get_redis()
    active_key = _active_key(queue_id)
    # SREM atomiškas: dvigubas paspaudimas antrą kartą gaus 0 ir 409
    if not await r.srem(active_key, user.user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Nesi pasižymėjęs šioje eilėje")

    now = datetime.now(timezone.utc)
    doc = await get_db().checkins.find_one_and_update(
        {"queue_id": ObjectId(queue_id), "user_id": ObjectId(user.user_id), "checked_out_at": None},
        {"$set": {"checked_out_at": now}},
        sort=[("checked_in_at", DESCENDING)],
        projection={"checked_in_at": 1},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        # Redis ir MongoDB išsiskyrė: atviro įrašo nėra, nors vartotojas buvo rinkinyje
        await invalidate_queue(queue_id)
        raise HTTPException(status.HTTP_409_CONFLICT, "Nesi pasižymėjęs šioje eilėje")

    duration_sec = int((now - doc["checked_in_at"]).total_seconds())
    active_count = await r.scard(active_key)
    await invalidate_queue(queue_id)
    await track_event("checkout", user_id=user.user_id, queue_id=queue_id, duration_sec=duration_sec)

    return CheckoutOut(
        queue_id=queue_id,
        checked_in_at=doc["checked_in_at"],
        checked_out_at=now,
        duration_sec=duration_sec,
        active_count=active_count,
    )
