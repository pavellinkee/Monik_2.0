"""
Net profit result model.

Responsibility:
    Represents the final profit calculation after gas costs.

Does NOT:
    - calculate gas;
    - access external APIs;
    - access the database;
    - filter opportunities;
    - send notifications.

The model is immutable.
"""

from __future__ import annotations

from decimal import Decimal

from models.arbitrage_opportunity import ArbitrageOpportunity
from models.base_model import BaseModel
from models.gas_cost import GasCost


class NetProfitResult(BaseModel):
    """
    Immutable result of final arbitrage profitability calculation.
    """

    opportunity: ArbitrageOpportunity
    gas_cost: GasCost

    gross_profit_usdt: Decimal
    gas_cost_usdt: Decimal
    net_profit_usdt: Decimal
    net_profit_percent: Decimal

    @property
    def is_profitable(self) -> bool:
        """
        Return True only when the final profit after gas is positive.
        """
        return self.net_profit_usdt > Decimal("0")
