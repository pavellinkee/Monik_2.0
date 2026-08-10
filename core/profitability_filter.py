cat > core/profitability_filter.py <<'PY'
"""
Profitability filter.

Responsibility:
    Keep only arbitrage opportunities whose final net profit
    after gas costs is positive.

Input:
    NetProfitResult objects.

Output:
    Tuple containing only profitable results.

Does NOT:
    - calculate profit;
    - calculate gas;
    - access external APIs;
    - access the database;
    - send notifications.

Compatibility:
    Primary:
        filter_profitable()

    Legacy compatibility alias:
        filter()
"""

from __future__ import annotations

from collections.abc import Iterable

from models.net_profit import NetProfitResult


class ProfitabilityFilter:
    """
    Filters final arbitrage results by net profitability.
    """

    def filter_profitable(
        self,
        results: Iterable[NetProfitResult],
    ) -> tuple[NetProfitResult, ...]:
        """
        Return only results with positive net profit.
        """
        if isinstance(results, (str, bytes)):
            raise TypeError(
                "results must be an iterable of NetProfitResult."
            )

        try:
            items = tuple(results)
        except TypeError as exc:
            raise TypeError(
                "results must be an iterable of NetProfitResult."
            ) from exc

        for result in items:
            if not isinstance(result, NetProfitResult):
                raise TypeError(
                    "every item in results must be a "
                    "NetProfitResult."
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
        Legacy compatibility alias for filter_profitable().
        """
        return self.filter_profitable(results)
PY
