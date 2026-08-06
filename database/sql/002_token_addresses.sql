-- ==========================================================
-- Table: token_addresses
-- Responsibility:
--   Stores token contract addresses for supported networks.
-- ==========================================================

CREATE TABLE IF NOT EXISTS token_addresses (
    id INTEGER PRIMARY KEY,

    token_id INTEGER NOT NULL,
    chain_id INTEGER NOT NULL,

    address TEXT NOT NULL,
    decimals INTEGER NOT NULL,

    availability INTEGER NOT NULL DEFAULT 1,

    FOREIGN KEY (token_id)
        REFERENCES tokens(id)
        ON DELETE CASCADE,

    UNIQUE(token_id, chain_id)
);

CREATE INDEX IF NOT EXISTS idx_token_addresses_token
ON token_addresses(token_id);

CREATE INDEX IF NOT EXISTS idx_token_addresses_chain
ON token_addresses(chain_id);

CREATE INDEX IF NOT EXISTS idx_token_addresses_availability
ON token_addresses(availability);
