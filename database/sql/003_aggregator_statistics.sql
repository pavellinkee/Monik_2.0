-- ==========================================================
-- Table: aggregator_statistics
-- Responsibility:
--   Stores quality metrics for each aggregator.
-- ==========================================================

CREATE TABLE IF NOT EXISTS aggregator_statistics (
    id INTEGER PRIMARY KEY,

    aggregator_name TEXT NOT NULL UNIQUE,

    successful_requests INTEGER NOT NULL DEFAULT 0,
    failed_requests INTEGER NOT NULL DEFAULT 0,

    average_latency_ms REAL NOT NULL DEFAULT 0,

    last_success_at TEXT,
    last_failure_at TEXT,

    last_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_aggregator_statistics_name
ON aggregator_statistics(aggregator_name);
