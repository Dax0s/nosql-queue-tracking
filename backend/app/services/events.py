"""Sending events to ClickHouse (spec section 9). Owner: person B."""

from typing import Literal

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


async def track_event(event_type: EventType, **fields) -> None:
    """Writes an event to `queues.events`. Never raises to the caller.

    Allowed `fields`: user_id, user_age, queue_id, lat, lng, score, duration_sec
    (missing ones are filled with defaults; event_time = now).

    TODO(B): insert with `settings={"async_insert": 1, "wait_for_async_insert": 0}`,
    only log errors.
    """
    return None
