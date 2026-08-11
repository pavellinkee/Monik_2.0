"""
Telegram alert manager.

Responsibility:
    Coordinate formatting, deduplication, best-opportunity
    selection and Telegram transport.

The manager does NOT:
    - calculate arbitrage;
    - calculate gas;
    - access aggregator APIs;
    - access SQL directly.
"""

from __future__ import annotations

from collections.abc import Iterable

from core.alert_deduplicator import AlertDeduplicator
from core.best_opportunity_selector import (
    BestOpportunitySelector,
)
from core.telegram_formatter import TelegramFormatter
from core.telegram_transport import TelegramTransport
from models.net_profit import NetProfitResult
from models.telegram_alert import TelegramAlert


class TelegramAlertManager:
    """
    Manages final Telegram alerts.
    """

    def __init__(
        self,
        transport: TelegramTransport,
        *,
        formatter: TelegramFormatter | None = None,
        deduplicator: AlertDeduplicator | None = None,
        selector: BestOpportunitySelector | None = None,
    ) -> None:
        if not isinstance(
            transport,
            TelegramTransport,
        ):
            raise TypeError(
                "transport must implement "
                "TelegramTransport."
            )

        self._transport = transport

        self._formatter = (
            formatter
            or TelegramFormatter()
        )

        self._deduplicator = (
            deduplicator
            or AlertDeduplicator()
        )

        self._selector = (
            selector
            or BestOpportunitySelector()
        )

    async def send_best(
        self,
        results: Iterable[NetProfitResult],
    ) -> TelegramAlert | None:
        """
        Select and send the best profitable opportunity.

        Returns:
            TelegramAlert when a new alert was sent.
            None when there was nothing to send.
        """

        best = self._selector.select(
            results
        )

        if best is None:
            return None

        alert = self._formatter.format(
            best
        )

        if self._deduplicator.check_and_remember(
            alert.alert_key
        ):
            return None

        await self._transport.send_message(
            alert.message
        )

        return alert

    async def send_all(
        self,
        results: Iterable[NetProfitResult],
    ) -> tuple[TelegramAlert, ...]:
        """
        Send all unique profitable opportunities.

        Results are processed in descending profitability order.
        """

        items = tuple(results)

        for result in items:
            if not isinstance(
                result,
                NetProfitResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "NetProfitResult objects."
                )

        profitable = tuple(
            result
            for result in items
            if result.is_profitable
        )

        ordered = tuple(
            sorted(
                profitable,
                key=lambda item: (
                    item.net_profit_usdt,
                    item.net_profit_percent,
                ),
                reverse=True,
            )
        )

        sent: list[TelegramAlert] = []

        for result in ordered:
            alert = self._formatter.format(
                result
            )

            if self._deduplicator.check_and_remember(
                alert.alert_key
            ):
                continue

            await self._transport.send_message(
                alert.message
            )

            sent.append(alert)

        return tuple(sent)

    async def notify(
        self,
        results: Iterable[NetProfitResult],
    ) -> TelegramAlert | None:
        """
        Legacy compatibility alias for send_best().
        """
        return await self.send_best(
            results
        )
