"""
Best opportunity selector.

Responsibility:
    Select the strongest profitable opportunity from a collection.

Default ranking:
    1. net_profit_usdt
    2. net_profit_percent

The selector does NOT:
    - calculate profitability;
    - send Telegram messages;
    - access SQL;
    - access APIs.
"""

from __future__ import annotations

from collections.abc import Iterable

from models.net_profit import NetProfitResult


class BestOpportunitySelector:
    """
    Selects the best profitable opportunity.
    """

    def select(
        self,
        results: Iterable[NetProfitResult],
    ) -> NetProfitResult | None:
        """
        Return the strongest profitable result.

        Returns None when no profitable result exists.
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

        if not profitable:
            return None

        return max(
            profitable,
            key=self._ranking_key,
        )

    def select_best(
        self,
        results: Iterable[NetProfitResult],
    ) -> NetProfitResult | None:
        """
        Compatibility alias for select().
        """
        return self.select(
            results
        )

    @staticmethod
    def _ranking_key(
        result: NetProfitResult,
    ) -> tuple:
        return (
            result.net_profit_usdt,
            result.net_profit_percent,
        )
