"""„Mano eilės“ (jei spėsim)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.deps import UserOnly
from app.models.schemas import MyQueueOut

router = APIRouter(prefix="/me", tags=["Vartotojas"])


@router.get("/queues", response_model=list[MyQueueOut], summary="Mano eilės")
async def my_queues(user: UserOnly, page: Annotated[int, Query(ge=1)] = 1):
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")
