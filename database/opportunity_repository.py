"""
SQL opportunity repository.

Responsibility:
    Persist profitable arbitrage opportunities through the
    existing database abstraction.

The repository does NOT:
    - calculate profitability;
    - validate opportunities;
    - send Telegram messages;
    - make aggregator requests.
"""

from __future__ import annotations

from collections.abc import Iterable

from core.opportunity_repository import (
    OpportunityRepository,
)
from models.net_profit import NetProfitResult


class SqlOpportunityRepository(
    OpportunityRepository
):
    """
    Database-backed opportunity repository.

    The database object is injected so the repository remains
    independent from a particular SQL implementation.
    """

    def __init__(
        self,
        database,
    ) -> None:
        if database is None:
            raise ValueError(
                "database cannot be None."
            )

        self._database = database

    async def save(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Persist one profitable opportunity.
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
                "Only profitable results can be stored."
            )

        await self._database.execute(
            """
            INSERT INTO opportunities (
                chain_id,
                base_symbol,
                target_symbol,
                buy_aggregator,
                sell_aggregator,
                amount_usdt,
                gross_profit_usdt,
                gas_cost_usdt,
                net_profit_usdt,
                net_profit_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.opportunity.chain_id,
                result.opportunity.base_symbol,
                result.opportunity.target_symbol,
                result.opportunity.buy_aggregator,
                result.opportunity.sell_aggregator,
                str(
                    result.opportunity.amount_usdt
                ),
                str(
                    result.gross_profit_usdt
                ),
                str(
                    result.gas_cost_usdt
                ),
                str(
                    result.net_profit_usdt
                ),
                str(
                    result.net_profit_percent
                ),
            ),
        )

    async def save_many(
        self,
        results: Iterable[NetProfitResult],
    ) -> int:
        """
        Persist multiple profitable results.

        Returns the number of stored results.
        """

        items = tuple(results)

        stored = 0

        for result in items:
            if not isinstance(
                result,
                NetProfitResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "NetProfitResult objects."
                )

            if not result.is_profitable:
                continue

            await self.save(result)
            stored += 1

        return stored

    async def exists(
        self,
        result: NetProfitResult,
    ) -> bool:
        """
        Check whether an equivalent opportunity exists.
        """

        if not isinstance(
            result,
            NetProfitResult,
        ):
            raise TypeError(
                "result must be a NetProfitResult."
            )

        row = await self._database.fetch_one(
            """
            SELECT 1
            FROM opportunities
            WHERE chain_id = ?
              AND base_symbol = ?
              AND target_symbol = ?
              AND buy_aggregator = ?
              AND sell_aggregator = ?
              AND amount_usdt = ?
              AND net_profit_usdt = ?
            LIMIT 1
            """,
            (
                result.opportunity.chain_id,
                result.opportunity.base_symbol,
                result.opportunity.target_symbol,
                result.opportunity.buy_aggregator,
                result.opportunity.sell_aggregator,
                str(
                    result.opportunity.amount_usdt
                ),
                str(
                    result.net_profit_usdt
                ),
            ),
        )

        return row is not None

    async def count(self) -> int:
        """
        Return number of stored opportunities.
        """

        row = await self._database.fetch_one(
            """
            SELECT COUNT(*)
            AS count
            FROM opportunities
            """
        )

        if row is None:
            return 0

        return int(
            row["count"]
        )

    async def store(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Legacy compatibility alias.
        """

        await self.save(result)
