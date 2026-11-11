"""Įvertinimai. Atsakingas: žmogus B."""

from fastapi import APIRouter, HTTPException, status

from app.auth.deps import UserOnly
from app.models.schemas import ReviewIn

router = APIRouter(prefix="/queues", tags=["Įvertinimai"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


@router.post("/{queue_id}/review", status_code=201, summary="Įvertinti eilę (1–5, tik kartą)")
async def create_review(queue_id: str, body: ReviewIn, user: UserOnly):
    # TODO(B): insert (DuplicateKeyError -> 409), rating_sum/rating_count,
    # add_weight(..., "review"), invalidate_queue, track_event("review_created")
    raise _TODO
