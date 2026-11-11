CREATE DATABASE IF NOT EXISTS queues;

CREATE TABLE IF NOT EXISTS queues.events (
    event_time    DateTime,
    event_type    LowCardinality(String),
    user_id       String,
    user_age      UInt8,
    queue_id      String,
    lat           Float64,
    lng           Float64,
    score         UInt8,
    duration_sec  UInt32
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_type, event_time);
