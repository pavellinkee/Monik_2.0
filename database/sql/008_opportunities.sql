CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    chain_id INTEGER NOT NULL,

    base_symbol TEXT NOT NULL,
    target_symbol TEXT NOT NULL,

    buy_aggregator TEXT NOT NULL,
    sell_aggregator TEXT NOT NULL,

    amount_usdt TEXT NOT NULL,

    gross_profit_usdt TEXT NOT NULL,
    gas_cost_usdt TEXT NOT NULL,

    net_profit_usdt TEXT NOT NULL,
    net_profit_percent TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS
idx_opportunities_chain
ON opportunities (
    chain_id
);

CREATE INDEX IF NOT EXISTS
idx_opportunities_created_at
ON opportunities (
    created_at
);

CREATE INDEX IF NOT EXISTS
idx_opportunities_net_profit
ON opportunities (
    net_profit_usdt
);

CREATE INDEX IF NOT EXISTS
idx_opportunities_route
ON opportunities (
    chain_id,
    base_symbol,
    target_symbol,
    buy_aggregator,
    sell_aggregator
);
