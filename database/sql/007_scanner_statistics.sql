-- ==========================================================
-- Table: scanner_statistics
-- Responsibility:
--   Stores cumulative scanner statistics.
-- ==========================================================

CREATE TABLE IF NOT EXISTS scanner_statistics (
    id INTEGER PRIMARY KEY CHECK (id = 1),

    scan_cycles INTEGER NOT NULL DEFAULT 0,
    quotes_requested INTEGER NOT NULL DEFAULT 0,
    opportunities_found INTEGER NOT NULL DEFAULT 0,
    opportunities_validated INTEGER NOT NULL DEFAULT 0
);
