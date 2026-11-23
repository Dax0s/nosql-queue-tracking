"""Komentarai ir likai. Atsakingas: žmogus B."""

from datetime import datetime, timezone
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ReturnDocument

from app.auth.deps import OptionalUser, UserOnly
from app.db.mongo import get_db
from app.db.redis import get_redis
from app.models.schemas import BadgeOut, CommentCreateIn, CommentOut, CommentsPage
from app.config import settings
from app.services.cache import cache_delete, cache_get, cache_set, invalidate_queue
from app.services.events import track_event

router = APIRouter(tags=["Komentarai"])

@router.get(
    "/queues/{queue_id}/comments",
    response_model=CommentsPage,
    summary="Komentarai su ženkleliais (cache 30 s)",
)
async def list_comments(queue_id: str, user: OptionalUser, page: Annotated[int, Query(ge=1)] = 1):
    # Naujausi pirmi. Bendra dalis cache'inama 30 s, liked_by_me pridedamas kiekvienai užklausai
    if not ObjectId.is_valid(queue_id):
        raise HTTPException(404, "Eilė nerasta")

    key = f"cache:queue:{queue_id}:comments:{page}"
    data = await cache_get(key)
    if data is None:
        data = await _load_comments_page(queue_id, page)
        await cache_set(key, data, settings.cache_ttl_comments)

    result = CommentsPage(**data)
    if user is not None and result.items:
        # liked_by į cache nepatenka, todėl vartotojo likus tikrinam atskira užklausa
        liked = await get_db().comments.distinct("_id", {
            "_id": {"$in": [ObjectId(c.id) for c in result.items]},
            "liked_by": ObjectId(user.user_id),
        })
        liked_ids = {str(i) for i in liked}
        for c in result.items:
            c.liked_by_me = c.id in liked_ids
    return result


async def _load_comments_page(queue_id: str, page: int) -> dict:
    """Komentarų puslapis iš MongoDB su autorių vardais ir ženkleliais (be vartotojo būsenos)."""
    db = get_db()
    qid = ObjectId(queue_id)
    if await db.queues.find_one({"_id": qid}, {"_id": 1}) is None:
        raise HTTPException(404, "Eilė nerasta")

    size = settings.comments_page_size
    # Imam vienu daugiau, kad sužinotume, ar yra kitas puslapis.
    # liked_by nereikalingas sąrašui (gali būti tūkstančiai id), todėl jo netraukiam iš Mongo
    docs = await (
        db.comments.find({"queue_id": qid}, {"liked_by": 0})
        .sort("created_at", -1)
        .skip((page - 1) * size)
        .limit(size + 1)
        .to_list(None)
    )
    has_more = len(docs) > size
    docs = docs[:size]

    author_ids = list({d["user_id"] for d in docs})
    authors = {
        a["_id"]: a
        async for a in db.users.find(
            {"_id": {"$in": author_ids}}, {"first_name": 1, "last_name": 1, "total_likes": 1}
        )
    }
    badges = await get_badges()

    items = []
    for d in docs:
        a = authors.get(d["user_id"])
        items.append(CommentOut(
            id=str(d["_id"]), queue_id=queue_id, user_id=str(d["user_id"]),
            author_name=f"{a['first_name']} {a['last_name'][0]}." if a else "Ištrintas vartotojas",
            badge=badge_for(a.get("total_likes", 0) if a else 0, badges),
            text=d["text"], likes_count=d.get("likes_count", 0), created_at=d["created_at"],
        ))
    return CommentsPage(items=items, page=page, has_more=has_more).model_dump(mode="json")


async def get_badges() -> list[dict]:
    """Ženklelių lygiai, nuo didžiausio (cache:badges, 1 h)."""
    badges = await cache_get("cache:badges")
    if badges is None: #TODO: zenkleliai nelabai keiciasi kodel tik vienai valandai cache?
        badges = await get_db().badges.find({}, {"_id": 0}).sort("min_likes", -1).to_list(None)
        await cache_set("cache:badges", badges, settings.cache_ttl_badges) 
    return badges


def badge_for(total_likes: int, badges: list[dict]) -> BadgeOut | None:
    """Aukščiausias ženklelis, kurio min_likes <= total_likes."""
    for b in badges:  # surikiuota nuo didžiausio
        if b["min_likes"] <= total_likes:
            return BadgeOut(**b)
    return None


@router.post(
    "/queues/{queue_id}/comments",
    response_model=CommentOut,
    status_code=201,
    summary="Naujas komentaras (max 5 per minutę)",
)
async def create_comment(queue_id: str, body: CommentCreateIn, user: UserOnly):
    # TODO(B): add_weight(..., "comment")
    db, r = get_db(), get_redis()
    if not ObjectId.is_valid(queue_id):
        raise HTTPException(404, "Eilė nerasta")
    queue = await db.queues.find_one({"_id": ObjectId(queue_id)})
    if queue is None:
        raise HTTPException(404, "Eilė nerasta")

    author = await db.users.find_one(
        {"_id": ObjectId(user.user_id)}, {"first_name": 1, "last_name": 1, "total_likes": 1}
    )
    if author is None:
        raise HTTPException(401, "Vartotojas nerastas")

    key = f"rl:comment:{user.user_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, settings.comment_rate_window_sec) ##TODO: jei numirs servas, kai count=1 o sita salyga ner patrigerinta bus riesta.
    if count > settings.comment_rate_limit:
        raise HTTPException(429, "Per daug komentarų, palauk minutę")
    #add comment
    now = datetime.now(timezone.utc)
    doc = {"queue_id": queue["_id"], "user_id": ObjectId(user.user_id),
           "text": body.text, "likes_count": 0, "liked_by": [], "created_at": now}
    result = await db.comments.insert_one(doc)

    # queue counters 
    await db.queues.update_one({"_id": queue["_id"]}, {"$inc": {"comment_count": 1}})
    await invalidate_queue(queue_id)
    await track_event("comment_created", user_id=user.user_id, queue_id=queue_id)

    #TODO turi padideti svoris

    return CommentOut(
        id=str(result.inserted_id), queue_id=queue_id, user_id=user.user_id,
        author_name=f"{author['first_name']} {author['last_name'][0]}.",
        badge=badge_for(author.get("total_likes", 0), await get_badges()), 
        text=body.text, likes_count=0, created_at=now,
    )


@router.delete("/comments/{comment_id}", status_code=204, summary="Ištrinti savo komentarą")
async def delete_comment(comment_id: str, user: UserOnly):
    # Tik autorius (403); likai ištrinami kartu su dokumentu, comment_count--, total_likes -= likes_count
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

    await db.queues.update_one({"_id": doc["queue_id"]}, {"$inc": {"comment_count": -1}})
    if doc.get("likes_count", 0):
        await db.users.update_one(
            {"_id": author_id}, {"$inc": {"total_likes": -doc["likes_count"]}}
        )
    await invalidate_queue(str(doc["queue_id"]))

    


@router.post("/comments/{comment_id}/like", status_code=201, summary="Palikinti komentarą")
async def like_comment(comment_id: str, user: UserOnly):
    # Savo komentaro negalima (400), antras likas -> 409,
    # likes_count++, autoriaus total_likes++
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(404, "Komentaras nerastas")

    db = get_db()
    oid = ObjectId(comment_id)
    liker_id = ObjectId(user.user_id)

    # Vienas atominis update viename dokumente: filtras užtikrina vieną liką
    # ir ne savo komentarą, net jei paspausta du kartus
    updated = await db.comments.find_one_and_update(
        {"_id": oid, "user_id": {"$ne": liker_id}, "liked_by": {"$ne": liker_id}},
        {"$push": {"liked_by": liker_id}, "$inc": {"likes_count": 1}},
        projection={"user_id": 1, "queue_id": 1, "likes_count": 1},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        # Nepavyko: išsiaiškinam kodėl (tik klaidos atveju)
        comment = await db.comments.find_one({"_id": oid}, {"user_id": 1})
        if comment is None:
            raise HTTPException(404, "Komentaras nerastas")
        if comment["user_id"] == liker_id:
            raise HTTPException(400, "Negalima likinti savo komentaro")
        raise HTTPException(409, "Jau palikinta")

    await db.users.update_one({"_id": updated["user_id"]}, {"$inc": {"total_likes": 1}})
    await cache_delete(f"cache:queue:{updated['queue_id']}:comments:1")
    await track_event("comment_liked", user_id=user.user_id, queue_id=str(updated["queue_id"]))
    return {"likes_count": updated["likes_count"]}


@router.delete("/comments/{comment_id}/like", status_code=204, summary="Atšaukti liką")
async def unlike_comment(comment_id: str, user: UserOnly):
    # Atšaukia savo liką: likes_count--, autoriaus total_likes--. Nėra liko -> 404
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(404, "Komentaras nerastas")

    db = get_db()
    oid = ObjectId(comment_id)
    liker_id = ObjectId(user.user_id)

    # Atomiškai: dvigubas paspaudimas negali atšaukti to paties liko du kartus
    comment = await db.comments.find_one_and_update(
        {"_id": oid, "liked_by": liker_id},
        {"$pull": {"liked_by": liker_id}, "$inc": {"likes_count": -1}},
        projection={"user_id": 1, "queue_id": 1},
    )
    if comment is None:
        raise HTTPException(404, "Likas nerastas")

    await db.users.update_one({"_id": comment["user_id"]}, {"$inc": {"total_likes": -1}})
    await cache_delete(f"cache:queue:{comment['queue_id']}:comments:1")
