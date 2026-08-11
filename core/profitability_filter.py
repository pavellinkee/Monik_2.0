"""
Profitability filter.

Responsibility:
    Keep only arbitrage results with positive net profit.

Input:
    NetProfitResult objects.

Output:
    Tuple containing only profitable results.

Does NOT:
    - calculate gas;
    - calculate net profit;
    - access external APIs;
    - access the database;
    - modify results;
    - send notifications.

Compatibility:
    Primary interface:
        filter_results()

    Legacy compatibility alias:
        filter()
"""

from __future__ import annotations

from collections.abc import Iterable

from models.net_profit import NetProfitResult


class ProfitabilityFilter:
    """
    Filters final arbitrage results by positive net profit.
    """

    def __init__(self) -> None:
        """Create a profitability filter."""
        pass

    def filter_results(
        self,
        results: Iterable[NetProfitResult],
    ) -> tuple[NetProfitResult, ...]:
        """
        Return only results with positive net profit.

        Original order is preserved.
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

        return tuple(
            result
            for result in items
            if result.is_profitable
        )

    def filter(
        self,
        results: Iterable[NetProfitResult],
    ) -> tuple[NetProfitResult, ...]:
        """
        Legacy compatibility alias.
        """

        return self.filter_results(results)
