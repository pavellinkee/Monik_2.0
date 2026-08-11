"""
Telegram alert models.

Responsibility:
    Represent immutable Telegram alert data.

The models contain no Telegram API logic.
"""

from __future__ import annotations

from decimal import Decimal

from models.base_model import BaseModel


class TelegramAlert(BaseModel):
    """
    Immutable Telegram alert.
    """

    alert_key: str

    chain_id: int

    base_symbol: str
    target_symbol: str

    buy_aggregator: str
    sell_aggregator: str

    amount_usdt: Decimal

    gross_profit_usdt: Decimal
    gas_cost_usdt: Decimal
    net_profit_usdt: Decimal
    net_profit_percent: Decimal

    message: str

    @property
    def is_profitable(self) -> bool:
        """
        Return True when the alert represents positive net profit.
        """
        return self.net_profit_usdt > Decimal("0")
