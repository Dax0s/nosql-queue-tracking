"""Eilės ir žemėlapis. Atsakingas: žmogus A."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.deps import OptionalUser, UserOnly
from app.models.schemas import MapPoint, QueueCreateIn, QueueOut

router = APIRouter(prefix="/queues", tags=["Eilės ir žemėlapis"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


# Turi būti aukščiau už /{queue_id}
@router.get("/map", response_model=list[MapPoint], summary="Žemėlapio taškai (cache 30 s)")
async def get_map(
    min_lat: Annotated[float, Query(ge=-90, le=90)],
    min_lng: Annotated[float, Query(ge=-180, le=180)],
    max_lat: Annotated[float, Query(ge=-90, le=90)],
    max_lng: Annotated[float, Query(ge=-180, le=180)],
    zoom: Annotated[int, Query(ge=0, le=20)],
):
    # TODO(A): bbox apvalinimas iki tinklelio, cache:map:{zoom}:{bbox_hash},
    # $geoWithin + expires_at > dabar
    raise _TODO


@router.post("", response_model=QueueOut, status_code=201, summary="Nauja eilė")
async def create_queue(body: QueueCreateIn, user: UserOnly):
    # TODO(A): insert, add_weight(..., "create"), track_event("queue_created")
    raise _TODO


@router.get("/{queue_id}", response_model=QueueOut, summary="Eilės suvestinė (cache 30 s)")
async def get_queue(queue_id: str, user: OptionalUser):
    # TODO(A): cache:queue:{id} + vartotojo būsena (SISMEMBER, review), track_event("queue_view")
    raise _TODO
