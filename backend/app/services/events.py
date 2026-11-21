import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal, get_args

from bson import ObjectId

from app.db.clickhouse import get_clickhouse
from app.db.mongo import get_db

log = logging.getLogger(__name__)

EventType = Literal[
    "register",
    "login",
    "queue_created",
    "queue_view",
    "checkin",
    "checkout",
    "comment_created",
    "review_created",
    "comment_liked",
]

_EVENT_TYPES = frozenset(get_args(EventType))

_COLUMNS = (
    ("event_time", "DateTime"),
    ("event_type", "LowCardinality(String)"),
    ("user_id", "String"),
    ("user_age", "UInt8"),
    ("queue_id", "String"),
    ("lat", "Float64"),
    ("lng", "Float64"),
    ("score", "UInt8"),
    ("duration_sec", "UInt32"),
)
_COLUMN_NAMES = [name for name, _ in _COLUMNS]
_COLUMN_TYPES = [type_ for _, type_ in _COLUMNS]

_FIELDS: dict[str, tuple[Any, Any]] = {
    "user_id": (str, ""),
    "user_age": (lambda v: max(0, min(255, int(v))), 0),
    "queue_id": (str, ""),
    "lat": (float, 0.0),
    "lng": (float, 0.0),
    "score": (lambda v: max(0, min(255, int(v))), 0),
    "duration_sec": (lambda v: max(0, min(2**32 - 1, int(v))), 0),
}

_INSERT_SETTINGS = {"async_insert": 1, "wait_for_async_insert": 0}
_INSERT_TIMEOUT_SEC = 5.0
_MAX_PENDING = 1000

_pending: set[asyncio.Task] = set()


async def track_event(event_type: EventType, **fields) -> None:
    try:
        if event_type not in _EVENT_TYPES:
            log.warning("track_event: nežinomas įvykio tipas %r, praleidžiama", event_type)
            return

        row: dict[str, Any] = {"event_time": datetime.now(timezone.utc), "event_type": event_type}
        for name, (convert, default) in _FIELDS.items():
            row[name] = default
        for name, value in fields.items():
            if name not in _FIELDS:
                log.warning("track_event(%s): nežinomas laukas %r ignoruojamas", event_type, name)
                continue
            if value is None:
                continue
            try:
                row[name] = _FIELDS[name][0](value)
            except (TypeError, ValueError):
                log.warning("track_event(%s): bloga %s reikšmė %r ignoruojama", event_type, name, value)

        lookup_age = bool(row["user_id"]) and fields.get("user_age") is None

        if len(_pending) >= _MAX_PENDING:
            log.warning("track_event(%s): per daug laukiančių įrašų, įvykis išmestas", event_type)
            return
        task = asyncio.create_task(_insert(row, lookup_age))
        _pending.add(task)
        task.add_done_callback(_pending.discard)
    except Exception:
        log.exception("track_event(%s): nepavyko paruošti įvykio", event_type)


async def _insert(row: dict[str, Any], lookup_age: bool) -> None:
    try:
        async with asyncio.timeout(_INSERT_TIMEOUT_SEC):
            if lookup_age:
                row["user_age"] = await _user_age(row["user_id"])
            await get_clickhouse().insert(
                "events",
                [[row[name] for name in _COLUMN_NAMES]],
                column_names=_COLUMN_NAMES,
                column_type_names=_COLUMN_TYPES,
                settings=_INSERT_SETTINGS,
            )
    except Exception as exc:
        log.warning("track_event(%s): nepavyko įrašyti į ClickHouse: %r", row["event_type"], exc)


async def _user_age(user_id: str) -> int:
    if not ObjectId.is_valid(user_id):
        return 0
    try:
        doc = await get_db().users.find_one({"_id": ObjectId(user_id)}, {"birth_year": 1})
    except Exception as exc:
        log.warning("track_event: nepavyko gauti vartotojo %s amžiaus: %r", user_id, exc)
        return 0
    if not doc or "birth_year" not in doc:
        return 0
    return max(0, min(255, datetime.now(timezone.utc).year - int(doc["birth_year"])))


async def flush(timeout: float = 2.0) -> None:
    if _pending:
        await asyncio.wait(set(_pending), timeout=timeout)
