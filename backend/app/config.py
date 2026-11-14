from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_url: str = "mongodb://root:root@localhost:27017/queues?authSource=admin"
    mongo_db: str = "queues"
    redis_url: str = "redis://localhost:6379/0"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "queues"
    clickhouse_user: str = "app"
    clickhouse_password: str = "app"
    cors_origins: str = "http://localhost:5173"

    session_ttl_sec: int = 24 * 3600

    # Eilės svoris (spec. 6 skyrius)
    weight_decay_per_min: float = 1.0
    weight_max: float = 360.0
    weight_cooldown_sec: int = 900
    weight_points: dict[str, int] = {
        "create": 60,
        "checkin": 5,
        "review": 10,
        "comment": 7,
    }

    # Cache TTL sekundėmis (spec. 8 skyrius)
    cache_ttl_map: int = 30
    cache_ttl_queue: int = 30
    cache_ttl_comments: int = 30
    cache_ttl_badges: int = 3600
    cache_ttl_report: int = 600

    comments_page_size: int = 20
    comment_rate_limit: int = 5
    comment_rate_window_sec: int = 60


settings = Settings()
