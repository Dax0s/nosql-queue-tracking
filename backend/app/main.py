from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import clickhouse, mongo, redis
from app.routers import auth, checkins, comments, me, queues, reports, reviews


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo.connect()
    redis.connect()
    await clickhouse.connect()
    await mongo.ensure_indexes()
    yield
    await clickhouse.close()
    await redis.close()
    mongo.close()


app = FastAPI(
    title="Low IQueue",
    description="Eilės žemėlapyje: check-in, komentarai, įvertinimai ir analitika.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(queues.router)
app.include_router(checkins.router)
app.include_router(comments.router)
app.include_router(reviews.router)
app.include_router(me.router)
app.include_router(reports.router)


@app.get("/health", tags=["Sistema"], summary="DB jungčių būsena")
async def health():
    result = {}
    for name, ping in (("mongo", mongo.ping), ("redis", redis.ping), ("clickhouse", clickhouse.ping)):
        try:
            result[name] = await ping()
        except Exception as exc:  # rodome, kuri jungtis neveikia
            result[name] = f"error: {exc}"
    return result
