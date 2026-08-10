"""
Gas cost result model.

Responsibility:
    Represents the calculated gas cost of a round-trip operation.

Does NOT:
    - request gas prices;
    - communicate with external APIs;
    - calculate arbitrage profitability;
    - modify ArbitrageOpportunity;
    - access the database.

The model is immutable and contains only normalized values.
"""

from __future__ import annotations

from decimal import Decimal

from models.base_model import BaseModel


class GasCost(BaseModel):
    """
    Immutable gas-cost calculation for one round trip.
    """

    chain_id: int

    native_token_price_usdt: Decimal

    stage1_gas_native: Decimal
    stage2_gas_native: Decimal

    total_gas_native: Decimal
    total_gas_usdt: Decimal

    @property
    def is_zero(self) -> bool:
        """Return True when the total gas cost is zero."""
        return self.total_gas_native == Decimal("0")
