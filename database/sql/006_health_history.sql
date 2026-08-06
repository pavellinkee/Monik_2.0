-- ==========================================================
-- Table: health_history
-- Responsibility:
--   Stores recent health check results.
-- ==========================================================

CREATE TABLE IF NOT EXISTS health_history (
    id INTEGER PRIMARY KEY,

    status TEXT NOT NULL,

    cpu_usage REAL,
    memory_usage REAL,

    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_health_history_created_at
ON health_history(created_at);
