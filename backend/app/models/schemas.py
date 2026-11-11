"""Pydantic schemos (API kontraktas, spec. 10 skyrius)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

# --- Auth ---


class RegisterIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    birth_year: int = Field(ge=1900, le=2026)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    birth_year: int
    role: Literal["user", "admin"]
    total_likes: int = 0


class TokenOut(BaseModel):
    token: str
    user: UserOut


# --- Eilės ---


class QueueCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class MapPoint(BaseModel):
    id: str
    title: str
    lat: float
    lng: float
    weight: float
    intensity: float = Field(description="svoris_dabar / 360")


class QueueOut(BaseModel):
    id: str
    title: str
    lat: float
    lng: float
    weight: float
    expires_at: datetime
    rating_avg: float | None
    rating_count: int
    comment_count: int
    active_count: int
    avg_wait_sec: float | None
    wait_samples: int
    # Prisijungusio vartotojo būsena (svečiui None)
    is_checked_in: bool | None = None
    my_score: int | None = None


# --- Komentarai, įvertinimai ---


class BadgeOut(BaseModel):
    name: str
    min_likes: int
    icon: str


class CommentCreateIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class CommentOut(BaseModel):
    id: str
    queue_id: str
    user_id: str
    author_name: str
    badge: BadgeOut | None
    text: str
    likes_count: int
    created_at: datetime
    liked_by_me: bool | None = None


class CommentsPage(BaseModel):
    items: list[CommentOut]
    page: int
    has_more: bool


class ReviewIn(BaseModel):
    score: int = Field(ge=1, le=5)


# --- Mano eilės ---


class MyQueueOut(BaseModel):
    queue_id: str
    queue_title: str
    checked_in_at: datetime
    checked_out_at: datetime | None
    duration_sec: int | None
    my_score: int | None
