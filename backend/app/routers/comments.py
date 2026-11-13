"""Komentarai ir likai. Atsakingas: žmogus B."""

from datetime import datetime, timezone
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status

from app.auth.deps import OptionalUser, UserOnly
from app.db.mongo import get_db
from app.db.redis import get_redis
from app.models.schemas import CommentCreateIn, CommentOut, CommentsPage
from app.config import settings
from app.services.cache import invalidate_queue

router = APIRouter(tags=["Komentarai"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


@router.get(
    "/queues/{queue_id}/comments",
    response_model=CommentsPage,
    summary="Komentarai su ženkleliais (cache 30 s)",
)
async def list_comments(queue_id: str, user: OptionalUser, page: Annotated[int, Query(ge=1)] = 1):
    # TODO(B): cache:queue:{id}:comments:{page}, ženkleliai iš cache:badges
    raise _TODO


@router.post(
    "/queues/{queue_id}/comments",
    response_model=CommentOut,
    status_code=201,
    summary="Naujas komentaras (max 5 per minutę)",
)
async def create_comment(queue_id: str, body: CommentCreateIn, user: UserOnly):
    # TODO(B): rl:comment:{user_id} (429), insert, comment_count++, add_weight(..., "comment"),
    # invalidate_queue, track_event("comment_created")
    db, r = get_db(), get_redis()
    if not ObjectId.is_valid(queue_id):
        raise HTTPException(404, "Eilė nerasta")
    queue = await db.queues.find_one({"_id": ObjectId(queue_id)})
    if queue is None:
        raise HTTPException(404, "Eilė nerasta")

    key = f"rl:comment:{user.user_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, settings.comment_rate_window_sec)
    if count > settings.comment_rate_limit:
        raise HTTPException(429, "Per daug komentarų, palauk minutę")
    #add comment
    now = datetime.now(timezone.utc)
    doc = {"queue_id": queue["_id"], "user_id": ObjectId(user.user_id),
           "text": body.text, "likes_count": 0, "created_at": now}
    result = await db.comments.insert_one(doc)

    # queue counters 
    await db.queues.update_one({"_id": queue["_id"]}, {"$inc": {"comment_count": 1}})
    await invalidate_queue(queue_id)

    #TODO turi padideti svoris

    author = await db.users.find_one({"_id": ObjectId(user.user_id)})
    
    return CommentOut(
        id=str(result.inserted_id), queue_id=queue_id, user_id=user.user_id,
        author_name=f"{author['first_name']} {author['last_name'][0]}.",
        badge=None,  # TODO: look up from badges by author["total_likes"]
        text=body.text, likes_count=0, created_at=now,
    )


@router.delete("/comments/{comment_id}", status_code=204, summary="Ištrinti savo komentarą")
async def delete_comment(comment_id: str, user: UserOnly):
    # Tik autorius (403); trina likus, comment_count--, total_likes -= likes_count
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(404, "Komentaras nerastas")
    
    db = get_db()
    oid = ObjectId(comment_id)
    author_id = ObjectId(user.user_id)                     

    doc = await db.comments.find_one_and_delete({"_id": oid, "user_id": author_id}) ##TODO: adminas negali nutrint kito komentaro lol
    if doc is None:
        exists = await db.comments.find_one({"_id": oid}, {"_id": 1})
        if exists is None:
            raise HTTPException(404, "Komentaras nerastas")
        raise HTTPException(403, "Negali trinti kito komentaro")

    await db.comment_likes.delete_many({"comment_id": oid}) #TODO: tame paciame dokumente padarysim galbut?
    await db.queues.update_one({"_id": doc["queue_id"]}, {"$inc": {"comment_count": -1}})
    if doc.get("likes_count", 0):
        await db.users.update_one(
            {"_id": author_id}, {"$inc": {"total_likes": -doc["likes_count"]}}
        )
    await invalidate_queue(str(doc["queue_id"]))

    


@router.post("/comments/{comment_id}/like", status_code=201, summary="Palikinti komentarą")
async def like_comment(comment_id: str, user: UserOnly):
    # TODO(B): savo komentaro negalima (400), unikalus indeksas -> 409,
    # likes_count++, total_likes++, track_event("comment_liked")
    raise _TODO


@router.delete("/comments/{comment_id}/like", status_code=204, summary="Atšaukti liką")
async def unlike_comment(comment_id: str, user: UserOnly):
    raise _TODO
