"""FastAPI dependencies: current user and role checks."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.sessions import get_session

_bearer = HTTPBearer(auto_error=False)


class SessionUser(BaseModel):
    user_id: str
    role: str
    token: str


async def get_optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> SessionUser | None:
    """Returns None for guests (for public endpoints that include user state)."""
    if creds is None:
        return None
    session = await get_session(creds.credentials)
    if session is None:
        return None
    return SessionUser(user_id=session["user_id"], role=session["role"], token=creds.credentials)


async def get_current_user(
    user: Annotated[SessionUser | None, Depends(get_optional_user)],
) -> SessionUser:
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str):
    async def checker(user: Annotated[SessionUser, Depends(get_current_user)]) -> SessionUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return checker


OptionalUser = Annotated[SessionUser | None, Depends(get_optional_user)]
CurrentUser = Annotated[SessionUser, Depends(get_current_user)]
UserOnly = Annotated[SessionUser, Depends(require_role("user"))]
AdminOnly = Annotated[SessionUser, Depends(require_role("admin"))]
