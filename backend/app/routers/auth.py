from fastapi import APIRouter, HTTPException, status

from app.auth.deps import CurrentUser
from app.models.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Autentifikacija"])

_TODO = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Dar neįgyvendinta")


@router.post("/register", response_model=TokenOut, status_code=201, summary="Registracija")
async def register(body: RegisterIn):
    # TODO: bcrypt hash, users insert (409 jei email užimtas), create_session, track_event("register")
    raise _TODO


@router.post("/login", response_model=TokenOut, summary="Prisijungimas")
async def login(body: LoginIn):
    # TODO: tikrinti slaptažodį, create_session, track_event("login")
    raise _TODO


@router.post("/logout", status_code=204, summary="Atsijungimas")
async def logout(user: CurrentUser):
    # TODO: delete_session(user.token)
    raise _TODO


@router.get("/me", response_model=UserOut, summary="Dabartinis vartotojas")
async def me(user: CurrentUser):
    raise _TODO
