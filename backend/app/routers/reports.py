from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated, Any, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.deps import require_role
from app.config import settings
from app.db.clickhouse import get_clickhouse
from app.db.mongo import get_db
from app.models.schemas import (
    ActivityRow,
    AgeGroupRow,
    CheckinsRow,
    CheckoutRateOut,
    PopularQueueRow,
    WaitTimeRow,
)
from app.services.cache import cache_get, cache_set

router = APIRouter(
    prefix="/reports",
    tags=["Ataskaitos"],
    dependencies=[Depends(require_role("admin"))],
)

Period = Literal["day", "week", "month"]
DateFrom = Annotated[date | None, Query(alias="from", description="Imtinai, YYYY-MM-DD")]
DateTo = Annotated[date | None, Query(alias="to", description="Imtinai, YYYY-MM-DD")]

_BUCKET = {"day": "toDate", "week": "toMonday", "month": "toStartOfMonth"}
_STEP = {"day": "INTERVAL 1 DAY", "week": "INTERVAL 1 WEEK", "month": "INTERVAL 1 MONTH"}

DELETED_TITLE = "(deleted)"


async def _cached(name: str, params: dict[str, Any], load: Callable[[], Awaitable[Any]]) -> Any:
    key_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    key = f"cache:report:{name}:{key_params}"
    data = await cache_get(key)
    if data is None:
        data = await load()
        await cache_set(key, data, settings.cache_ttl_report)
    return data


async def _query(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    result = await get_clickhouse().query(sql, parameters={"tz": settings.report_tz, **params})
    return list(result.named_results())


def _date_filter(date_from: date | None, date_to: date | None) -> tuple[str, dict[str, Any]]:
    """WHERE dalis datų intervalui (vietos laiku, abu galai imtinai)."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "'from' negali būti vėliau nei 'to'")
    sql, params = "", {}
    if date_from:
        sql += " AND toDate(event_time, {tz:String}) >= {date_from:Date}"
        params["date_from"] = date_from
    if date_to:
        sql += " AND toDate(event_time, {tz:String}) <= {date_to:Date}"
        params["date_to"] = date_to
    return sql, params


def _period_fill(period: Period, date_from: date | None, date_to: date | None) -> str:
    fn = _BUCKET[period]
    sql = " WITH FILL"
    if date_from:
        sql += f" FROM {fn}({{date_from:Date}})"
    if date_to:
        sql += f" TO {fn}({{date_to:Date}}) + {_STEP[period]}"
    return sql + f" STEP {_STEP[period]}"


@router.get(
    "/activity",
    response_model=list[ActivityRow],
    summary="Nauji vartotojai ir eilės per periodą",
)
async def activity(period: Period = "day", date_from: DateFrom = None, date_to: DateTo = None):
    where, params = _date_filter(date_from, date_to)

    async def load():
        rows = await _query(
            f"""
            SELECT {_BUCKET[period]}(event_time, {{tz:String}}) AS period_start,
                   countIf(event_type = 'register')      AS new_users,
                   countIf(event_type = 'queue_created') AS new_queues
            FROM events
            WHERE event_type IN ('register', 'queue_created'){where}
            GROUP BY period_start
            ORDER BY period_start{_period_fill(period, date_from, date_to)}
            """,
            params,
        )
        return [ActivityRow(**r).model_dump(mode="json") for r in rows]

    return await _cached("activity", {"period": period, "from": date_from, "to": date_to}, load)


@router.get(
    "/checkins",
    response_model=list[CheckinsRow],
    summary="Check-in skaičius per periodą",
)
async def checkins(period: Period = "day", date_from: DateFrom = None, date_to: DateTo = None):
    where, params = _date_filter(date_from, date_to)

    async def load():
        rows = await _query(
            f"""
            SELECT {_BUCKET[period]}(event_time, {{tz:String}}) AS period_start,
                   count() AS checkins
            FROM events
            WHERE event_type = 'checkin'{where}
            GROUP BY period_start
            ORDER BY period_start{_period_fill(period, date_from, date_to)}
            """,
            params,
        )
        return [CheckinsRow(**r).model_dump(mode="json") for r in rows]

    return await _cached("checkins", {"period": period, "from": date_from, "to": date_to}, load)


@router.get(
    "/wait-times",
    response_model=list[WaitTimeRow],
    summary="Vid. laukimo laikas pagal savaitės dieną ir valandą",
    description="Be `queue_id` – visoms eilėms. Savaitės diena ir valanda – vietos laiku.",
)
async def wait_times(queue_id: str | None = None):
    if queue_id is not None and not ObjectId.is_valid(queue_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Netinkamas queue_id")

    async def load():
        where, params = "", {}
        if queue_id:
            where, params = " AND queue_id = {queue_id:String}", {"queue_id": queue_id}
        rows = await _query(
            f"""
            SELECT toDayOfWeek(event_time, 0, {{tz:String}}) AS weekday,
                   toHour(toTimeZone(event_time, {{tz:String}})) AS hour,
                   round(avg(duration_sec) / 60, 1) AS avg_wait_min,
                   count() AS samples
            FROM events
            WHERE event_type = 'checkout'{where}
            GROUP BY weekday, hour
            ORDER BY weekday, hour
            """,
            params,
        )
        return [WaitTimeRow(**r).model_dump(mode="json") for r in rows]

    return await _cached("wait-times", {"queue_id": queue_id or "all"}, load)


@router.get(
    "/popular-queues",
    response_model=list[PopularQueueRow],
    summary="Populiariausios eilės pagal peržiūras ir check-in",
    description="Ištrintų eilių pavadinimas – `(deleted)`.",
)
async def popular_queues(
    days: Annotated[int, Query(ge=1, le=365)] = 7,
    sort_by: Literal["views", "checkins"] = "views",
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    secondary = "checkins" if sort_by == "views" else "views"

    async def load():
        rows = await _query(
            f"""
            SELECT queue_id,
                   countIf(event_type = 'queue_view') AS views,
                   countIf(event_type = 'checkin')    AS checkins
            FROM events
            WHERE event_type IN ('queue_view', 'checkin')
              AND queue_id != ''
              AND event_time >= now() - INTERVAL {{days:UInt16}} DAY
            GROUP BY queue_id
            ORDER BY {sort_by} DESC, {secondary} DESC
            LIMIT {{limit:UInt16}}
            """,
            {"days": days, "limit": limit},
        )
        # Pavadinimai – iš MongoDB (ClickHouse saugo tik ID)
        ids = [ObjectId(r["queue_id"]) for r in rows if ObjectId.is_valid(r["queue_id"])]
        titles = {
            str(q["_id"]): q["title"]
            async for q in get_db().queues.find({"_id": {"$in": ids}}, {"title": 1})
        }
        return [
            PopularQueueRow(**r, title=titles.get(r["queue_id"], DELETED_TITLE)).model_dump(mode="json")
            for r in rows
        ]

    return await _cached("popular-queues", {"days": days, "sort_by": sort_by, "limit": limit}, load)


@router.get(
    "/checkout-rate",
    response_model=CheckoutRateOut,
    summary="Check-out dalis",
    description="Kokia dalis check-in užbaigiami check-out. Skaičiuojama pagal įvykių laiką intervale.",
)
async def checkout_rate(date_from: DateFrom = None, date_to: DateTo = None):
    where, params = _date_filter(date_from, date_to)

    async def load():
        [row] = await _query(
            f"""
            SELECT countIf(event_type = 'checkin')  AS checkins,
                   countIf(event_type = 'checkout') AS checkouts
            FROM events
            WHERE event_type IN ('checkin', 'checkout'){where}
            """,
            params,
        )
        rate = round(row["checkouts"] / row["checkins"], 4) if row["checkins"] else None
        return CheckoutRateOut(**row, rate=rate).model_dump(mode="json")

    return await _cached("checkout-rate", {"from": date_from, "to": date_to}, load)


@router.get(
    "/activity-by-age",
    response_model=list[AgeGroupRow],
    summary="Aktyvumas pagal amžiaus grupes",
    description="Visi įvykiai. `unknown` – svečiai ir vartotojai be amžiaus.",
)
async def activity_by_age():
    async def load():
        rows = await _query(
            """
            SELECT multiIf(user_age = 0,  'unknown',
                           user_age < 18, '<18',
                           user_age < 25, '18-24',
                           user_age < 35, '25-34',
                           user_age < 45, '35-44',
                                          '45+') AS age_group,
                   count() AS events,
                   uniqIf(user_id, user_id != '') AS users
            FROM events
            GROUP BY age_group
            ORDER BY min(user_age) = 0, min(user_age)
            """,
            {},
        )
        return [AgeGroupRow(**r).model_dump(mode="json") for r in rows]

    return await _cached("activity-by-age", {}, load)
