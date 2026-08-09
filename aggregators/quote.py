"""
Common quote model.

Responsibility:
    Defines the normalized quote returned by every aggregator.

Does NOT:
    - perform API requests;
    - calculate arbitrage;
    - validate profitability;
    - apply rate limits.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Quote:
    """Normalized aggregator quote."""

    aggregator: str

    chain_id: int

    token_in: str
    token_out: str

    amount_in: int
    amount_out: int

    gas_estimate: int | None

    gas_cost_native: Decimal | None

    price_impact: Decimal | None

    route: str | None

    timestamp: str
