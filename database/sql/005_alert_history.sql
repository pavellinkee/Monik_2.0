-- ==========================================================
-- Table: alert_history
-- Responsibility:
--   Stores sent alerts to prevent duplicates and spam.
-- ==========================================================

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY,

    alert_type TEXT NOT NULL,
    source TEXT NOT NULL,

    message TEXT NOT NULL,

    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_history_created_at
ON alert_history(created_at);

CREATE INDEX IF NOT EXISTS idx_alert_history_source
ON alert_history(source);
