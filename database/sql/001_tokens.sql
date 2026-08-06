-- ==========================================================
-- Table: tokens
-- Responsibility:
--   Stores logical token definitions.
-- ==========================================================

CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,

    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    coingecko_id TEXT NOT NULL,

    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100
);

CREATE INDEX IF NOT EXISTS idx_tokens_enabled
ON tokens(enabled);

CREATE INDEX IF NOT EXISTS idx_tokens_priority
ON tokens(priority);
