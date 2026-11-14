from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.auth.deps import CurrentUser
from app.auth.passwords import hash_password, verify_password
from app.auth.sessions import create_session, delete_session
from app.db.mongo import get_db
from app.models.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.services.events import track_event

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_out(doc: dict) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        email=doc["email"],
        first_name=doc["first_name"],
        last_name=doc["last_name"],
        birth_year=doc["birth_year"],
        role=doc["role"],
        total_likes=doc.get("total_likes", 0),
    )


def _age(birth_year: int) -> int:
    return max(0, min(255, datetime.now(timezone.utc).year - birth_year))


async def _start_session(doc: dict, event_type: str) -> TokenOut:
    user_id = str(doc["_id"])
    token = await create_session(user_id, doc["role"])
    await track_event(event_type, user_id=user_id, user_age=_age(doc["birth_year"]))
    return TokenOut(token=token, user=_user_out(doc))


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register",
    responses={409: {"description": "Email already registered"}},
)
async def register(body: RegisterIn):
    doc = {
        "email": body.email.lower(),
        "password_hash": await hash_password(body.password),
        "first_name": body.first_name,
        "last_name": body.last_name,
        "birth_year": body.birth_year,
        "role": "user",
        "total_likes": 0,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await get_db().users.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    doc["_id"] = result.inserted_id
    return await _start_session(doc, "register")


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Log in",
    responses={401: {"description": "Invalid email or password"}},
)
async def login(body: LoginIn):
    doc = await get_db().users.find_one({"email": body.email.lower()})
    if doc is None or not await verify_password(body.password, doc["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return await _start_session(doc, "login")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    responses={401: {"description": "Not authenticated"}},
)
async def logout(user: CurrentUser):
    await delete_session(user.token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Current user",
    responses={401: {"description": "Not authenticated"}},
)
async def me(user: CurrentUser):
    doc = await get_db().users.find_one({"_id": ObjectId(user.user_id)})
    if doc is None:
        await delete_session(user.token)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return _user_out(doc)
