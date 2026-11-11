"""Check-in / check-out (eiga – spec. 8 skyrius). Atsakingas: žmogus A."""

from fastapi import APIRouter, HTTPException, status

from app.auth.deps import UserOnly

router = APIRouter(prefix="/queues", tags=["Check-in"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


@router.post("/{queue_id}/checkin", status_code=201, summary="Pasižymėti eilėje")
async def checkin(queue_id: str, user: UserOnly):
    # TODO(A): redis_lock, expires_at tikrinimas, SISMEMBER -> 409, insert + SADD,
    # add_weight(..., "checkin"), invalidate_queue, track_event("checkin")
    raise _TODO


@router.post("/{queue_id}/checkout", summary="Išeiti iš eilės")
async def checkout(queue_id: str, user: UserOnly):
    # TODO(A): SISMEMBER -> 409, checked_out_at, SREM, invalidate_queue,
    # track_event("checkout", duration_sec=...)
    raise _TODO
