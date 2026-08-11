"""
Telegram alert formatter.

Responsibility:
    Convert a NetProfitResult into a human-readable Telegram
    message.

The formatter does NOT:
    - send messages;
    - access Telegram API;
    - access SQL;
    - calculate profitability.
"""

from __future__ import annotations

from decimal import Decimal

from models.net_profit import NetProfitResult
from models.telegram_alert import TelegramAlert


class TelegramFormatter:
    """
    Formats profitable opportunities for Telegram.
    """

    def __init__(
        self,
        *,
        decimals: int = 4,
    ) -> None:
        if decimals < 0:
            raise ValueError(
                "decimals cannot be negative."
            )

        self._decimals = decimals

    def format(
        self,
        result: NetProfitResult,
    ) -> TelegramAlert:
        """
        Format one profitable result.
        """

        if not isinstance(
            result,
            NetProfitResult,
        ):
            raise TypeError(
                "result must be a NetProfitResult."
            )

        if not result.is_profitable:
            raise ValueError(
                "Only profitable results can be "
                "formatted as alerts."
            )

        opportunity = result.opportunity

        alert_key = self.build_alert_key(
            result
        )

        message = (
            "💎 ARBITRAGE OPPORTUNITY\n\n"
            f"🌐 Chain: {opportunity.chain_id}\n"
            f"💱 Pair: "
            f"{opportunity.base_symbol}/"
            f"{opportunity.target_symbol}\n\n"
            f"🟢 Buy: "
            f"{opportunity.buy_aggregator}\n"
            f"🔴 Sell: "
            f"{opportunity.sell_aggregator}\n\n"
            f"💰 Amount: "
            f"{self._format_decimal(opportunity.amount_usdt)} "
            f"USDT\n"
            f"📈 Gross profit: "
            f"{self._format_decimal(result.gross_profit_usdt)} "
            f"USDT\n"
            f"⛽ Gas: "
            f"{self._format_decimal(result.gas_cost_usdt)} "
            f"USDT\n"
            f"✅ Net profit: "
            f"{self._format_decimal(result.net_profit_usdt)} "
            f"USDT\n"
            f"📊 Net profit: "
            f"{self._format_decimal(result.net_profit_percent)}%"
        )

        return TelegramAlert(
            alert_key=alert_key,
            chain_id=opportunity.chain_id,
            base_symbol=opportunity.base_symbol,
            target_symbol=opportunity.target_symbol,
            buy_aggregator=opportunity.buy_aggregator,
            sell_aggregator=opportunity.sell_aggregator,
            amount_usdt=opportunity.amount_usdt,
            gross_profit_usdt=result.gross_profit_usdt,
            gas_cost_usdt=result.gas_cost_usdt,
            net_profit_usdt=result.net_profit_usdt,
            net_profit_percent=result.net_profit_percent,
            message=message,
        )

    def build_alert_key(
        self,
        result: NetProfitResult,
    ) -> str:
        """
        Build a stable identity for an alert.

        Profit amount is included intentionally so that a materially
        changed opportunity can generate a new alert.
        """

        opportunity = result.opportunity

        return "|".join(
            (
                str(opportunity.chain_id),
                opportunity.base_symbol.upper(),
                opportunity.target_symbol.upper(),
                opportunity.buy_aggregator,
                opportunity.sell_aggregator,
                str(opportunity.amount_usdt),
                str(result.net_profit_usdt),
            )
        )

    def format_message(
        self,
        result: NetProfitResult,
    ) -> str:
        """
        Return only the formatted message.

        Compatibility helper.
        """
        return self.format(
            result
        ).message

    def _format_decimal(
        self,
        value: Decimal,
    ) -> str:
        return (
            f"{value:.{self._decimals}f}"
        )

    def build(
        self,
        result: NetProfitResult,
    ) -> TelegramAlert:
        """
        Legacy compatibility alias for format().
        """
        return self.format(
            result
        )
