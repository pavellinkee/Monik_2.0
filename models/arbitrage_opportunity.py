"""
Arbitrage opportunity model.

Responsibility:
    Represents the result of Stage 3 gross arbitrage analysis.

Does NOT:
    - calculate gas costs;
    - access external APIs;
    - access the database;
    - send notifications;
    - validate final executable profitability.

Stage 3 calculates gross round-trip performance only.
"""

from __future__ import annotations

from decimal import Decimal

from aggregators.quote import Quote
from models.base_model import BaseModel


class ArbitrageOpportunity(BaseModel):
    """
    Immutable result of a gross arbitrage analysis.

    Flow:

        Stage 1:
            base -> target

        Stage 2:
            target -> base

        Stage 3:
            compare initial base amount
            with final base amount.
    """

    chain_id: int

    base_symbol: str
    target_symbol: str

    amount_usdt: Decimal

    buy_aggregator: str
    sell_aggregator: str

    stage1_quote: Quote
    stage2_quote: Quote

    final_amount_base_units: int
    gross_profit_base_units: int

    gross_profit_usdt: Decimal
    gross_profit_percent: Decimal

    @property
    def is_gross_profitable(self) -> bool:
        """Return True when the gross round trip is profitable."""
        return self.gross_profit_base_units > 0
