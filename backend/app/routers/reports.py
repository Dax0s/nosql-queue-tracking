"""Ataskaitos iš ClickHouse (visos cache'inamos 10 min). Atsakingas: žmogus B."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.deps import require_role

router = APIRouter(
    prefix="/reports",
    tags=["Ataskaitos"],
    dependencies=[Depends(require_role("admin"))],
)

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")

Period = Literal["day", "week", "month"]
DateFrom = Annotated[date | None, Query(alias="from")]
DateTo = Annotated[date | None, Query(alias="to")]


@router.get("/activity", summary="Nauji vartotojai ir eilės per periodą")
async def activity(period: Period = "day", date_from: DateFrom = None, date_to: DateTo = None):
    raise _TODO


@router.get("/checkins", summary="Check-in skaičius per periodą")
async def checkins(period: Period = "day", date_from: DateFrom = None, date_to: DateTo = None):
    raise _TODO


@router.get("/wait-times", summary="Vid. laukimo laikas pagal savaitės dieną ir valandą")
async def wait_times(queue_id: str | None = None):
    raise _TODO


@router.get("/popular-queues", summary="Populiariausios eilės pagal peržiūras ir check-in")
async def popular_queues(days: Annotated[int, Query(ge=1, le=365)] = 7):
    raise _TODO


@router.get("/checkout-rate", summary="Check-out dalis")
async def checkout_rate(date_from: DateFrom = None, date_to: DateTo = None):
    raise _TODO


@router.get("/activity-by-age", summary="Aktyvumas pagal amžiaus grupes")
async def activity_by_age():
    raise _TODO
