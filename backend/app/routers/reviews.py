"""Įvertinimai. Atsakingas: žmogus B."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.auth.deps import UserOnly
from app.db.mongo import get_db
from app.models.schemas import ReviewIn
from app.services.cache import invalidate_queue

router = APIRouter(prefix="/queues", tags=["Įvertinimai"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


@router.post("/{queue_id}/review", status_code=201, summary="Įvertinti eilę (1–5, tik kartą)")
async def create_review(queue_id: str, body: ReviewIn, user: UserOnly):
    # Vienas įvertinimas vienam vartotojui (unikalus indeksas -> 409), pakeisti negalima.
    # rating_sum += score, rating_count++
    if not ObjectId.is_valid(queue_id):
        raise HTTPException(404, "Eilė nerasta")

    db = get_db()
    qid = ObjectId(queue_id)
    if await db.queues.find_one({"_id": qid}, {"_id": 1}) is None:
        raise HTTPException(404, "Eilė nerasta")

    # Unikalus indeksas (queue_id, user_id) garantuoja vieną įvertinimą, net jei paspausta du kartus
    try:
        await db.reviews.insert_one({
            "queue_id": qid, "user_id": ObjectId(user.user_id),
            "score": body.score, "created_at": datetime.now(timezone.utc),
        })
    except DuplicateKeyError:
        raise HTTPException(409, "Šią eilę jau įvertinai")

    queue = await db.queues.find_one_and_update(
        {"_id": qid}, {"$inc": {"rating_sum": body.score, "rating_count": 1}},
        projection={"rating_sum": 1, "rating_count": 1}, return_document=ReturnDocument.AFTER,
    )
    await invalidate_queue(queue_id) #TODO: istriname ir komentarus ar reik? Gal nelabai ir rupi?
    # TODO(A): add_weight(queue_id, user.user_id, "review"), kai bus įgyvendintas
    # TODO(B): track_event("review_created", user_id=..., queue_id=..., score=...), kai bus įgyvendintas

    return {
        "score": body.score,
        "rating_avg": round(queue["rating_sum"] / queue["rating_count"], 2),
        "rating_count": queue["rating_count"],
    }
