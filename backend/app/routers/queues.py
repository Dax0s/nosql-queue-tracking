"""Eilės ir žemėlapis. Atsakingas: žmogus A."""

import math
from datetime import datetime, timedelta, timezone
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status

from app.auth.deps import OptionalUser, UserOnly
from app.config import settings
from app.db.mongo import get_db
from app.models.schemas import MapPoint, QueueCreateIn, QueueOut
from app.services.cache import cache_get, cache_set
from app.services.events import track_event

router = APIRouter(prefix="/queues", tags=["Eilės ir žemėlapis"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


def _snap_bbox(
    min_lat: float, min_lng: float, max_lat: float, max_lng: float, zoom: int
) -> tuple[float, float, float, float]:
    cell = 360 / 2**zoom
    return (
        max(-90.0, math.floor(min_lat / cell) * cell),
        max(-180.0, math.floor(min_lng / cell) * cell),
        min(90.0, math.ceil(max_lat / cell) * cell),
        min(180.0, math.ceil(max_lng / cell) * cell),
    )


def _current_weight(doc: dict, now: datetime) -> float:
    minutes = (now - doc["weight_updated_at"]).total_seconds() / 60
    return max(0.0, doc["weight"] - settings.weight_decay_per_min * minutes)


# Must be declared before /{queue_id}
@router.get(
    "/map",
    response_model=list[MapPoint],
    summary="Map points (cached for 30 s)",
    responses={422: {"description": "Invalid bounding box"}},
)
async def get_map(
    min_lat: Annotated[float, Query(ge=-90, le=90)],
    min_lng: Annotated[float, Query(ge=-180, le=180)],
    max_lat: Annotated[float, Query(ge=-90, le=90)],
    max_lng: Annotated[float, Query(ge=-180, le=180)],
    zoom: Annotated[int, Query(ge=0, le=20)],
):
    if min_lat > max_lat or min_lng > max_lng:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid bounding box")

    south, west, north, east = _snap_bbox(min_lat, min_lng, max_lat, max_lng, zoom)
    key = f"cache:map:{zoom}:{south:.6f}:{west:.6f}:{north:.6f}:{east:.6f}"
    cached = await cache_get(key)
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)
    cursor = get_db().queues.find(
        {
            "location": {"$geoWithin": {"$box": [[west, south], [east, north]]}},
            "expires_at": {"$gt": now},
        },
        {"title": 1, "location": 1, "weight": 1, "weight_updated_at": 1},
    )
    points = []
    async for doc in cursor:
        weight = _current_weight(doc, now)
        lng, lat = doc["location"]["coordinates"]
        points.append(
            {
                "id": str(doc["_id"]),
                "title": doc["title"],
                "lat": lat,
                "lng": lng,
                "weight": weight,
                "intensity": weight / settings.weight_max,
            }
        )
    await cache_set(key, points, settings.cache_ttl_map)
    return points


@router.post(
    "",
    response_model=QueueOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a queue",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
    },
)
async def create_queue(body: QueueCreateIn, user: UserOnly):
    db = get_db()
    now = datetime.now(timezone.utc)
    weight = float(settings.weight_points["create"])
    expires_at = now + timedelta(minutes=weight / settings.weight_decay_per_min)
    result = await db.queues.insert_one(
        {
            "title": body.title,
            "location": {"type": "Point", "coordinates": [body.lng, body.lat]},
            "created_by": ObjectId(user.user_id),
            "created_at": now,
            "weight": weight,
            "weight_updated_at": now,
            "expires_at": expires_at,
            "rating_sum": 0,
            "rating_count": 0,
            "comment_count": 0,
        }
    )
    queue_id = str(result.inserted_id)

    creator = await db.users.find_one({"_id": ObjectId(user.user_id)}, {"birth_year": 1})
    age = max(0, min(255, now.year - creator["birth_year"])) if creator else 0
    await track_event(
        "queue_created",
        user_id=user.user_id,
        user_age=age,
        queue_id=queue_id,
        lat=body.lat,
        lng=body.lng,
    )

    return QueueOut(
        id=queue_id,
        title=body.title,
        lat=body.lat,
        lng=body.lng,
        weight=weight,
        expires_at=expires_at,
        rating_avg=None,
        rating_count=0,
        comment_count=0,
        active_count=0,
        avg_wait_sec=None,
        wait_samples=0,
        is_checked_in=False,
        my_score=None,
    )


@router.get("/{queue_id}", response_model=QueueOut, summary="Eilės suvestinė (cache 30 s)")
async def get_queue(queue_id: str, user: OptionalUser):
    # TODO(A): cache:queue:{id} + vartotojo būsena (SISMEMBER, review), track_event("queue_view")
    raise _TODO
