"""Įvykių siuntimas į ClickHouse (spec. 9 skyrius). Atsakingas: žmogus B."""

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
    """Įrašo įvykį į `queues.events`. Niekada nemeta klaidos kvietėjui.

    Galimi `fields`: user_id, user_age, queue_id, lat, lng, score, duration_sec
    (trūkstami užpildomi numatytosiomis reikšmėmis; event_time = dabar).

    TODO(B): insert su `settings={"async_insert": 1, "wait_for_async_insert": 0}`,
    klaidas tik log'inti.
    """
    raise NotImplementedError
