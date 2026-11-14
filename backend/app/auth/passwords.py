from fastapi.concurrency import run_in_threadpool
from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def hash_password(password: str) -> str:
    return await run_in_threadpool(_ctx.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await run_in_threadpool(_ctx.verify, password, password_hash)
