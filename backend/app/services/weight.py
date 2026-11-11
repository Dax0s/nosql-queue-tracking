"""Eilės svoris (spec. 6 skyrius). Atsakingas: žmogus A."""

from typing import Literal

WeightAction = Literal["create", "checkin", "review", "comment"]


async def add_weight(queue_id: str, user_id: str, action: WeightAction) -> bool:
    """Prideda eilei svorio už veiksmą. Grąžina False, jei suveikė pumpavimo apsauga.

    TODO(A):
    1. `SET weight:{queue_id}:{user_id}:{action} 1 NX EX 900`; jei nepavyko, return False.
    2. Vienas atominis MongoDB update su aggregation pipeline:
         weight            = min(360, max(0, weight − k·(dabar − weight_updated_at)) + taškai)
         weight_updated_at = dabar
         expires_at        = dabar + weight / k
    3. `EXPIREAT queue:{id}:active <expires_at>`.
    Konstantos: `settings.weight_points`, `weight_decay_per_min`, `weight_max`, `weight_cooldown_sec`.
    """
    raise NotImplementedError
