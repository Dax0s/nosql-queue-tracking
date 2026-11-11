import clickhouse_connect
from clickhouse_connect.driver import AsyncClient

from app.config import settings

_client: AsyncClient | None = None


async def connect() -> None:
    global _client
    _client = await clickhouse_connect.get_async_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_db,
    )


async def close() -> None:
    if _client is not None:
        await _client.close()


def get_clickhouse() -> AsyncClient:
    if _client is None:
        raise RuntimeError("ClickHouse neprijungta")
    return _client


async def ping() -> bool:
    result = await get_clickhouse().query("SELECT 1")
    return result.result_rows[0][0] == 1
