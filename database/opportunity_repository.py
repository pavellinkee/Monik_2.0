"""
SQL opportunity repository.

Responsibility:
    Persist profitable arbitrage opportunities through the
    existing DatabaseInterface.

Compatibility:
    - works with the existing DatabaseInterface;
    - works with SQLiteDatabase;
    - preserves OpportunityRepository;
    - preserves legacy store() alias.

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

        self._validate_result(
            result
        )

        await self._save_without_commit(
            result
        )

        await self._database.commit()

    async def _save_without_commit(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Persist one result without committing.

        Used internally by save_many() so that a batch is committed
        once instead of once per opportunity.
        """

        opportunity = result.opportunity

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
            opportunity.chain_id,
            opportunity.base_symbol,
            opportunity.target_symbol,
            opportunity.buy_aggregator,
            opportunity.sell_aggregator,
            str(
                opportunity.amount_usdt
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
        )

    async def save_many(
        self,
        results: Iterable[NetProfitResult],
    ) -> int:
        """
        Persist multiple profitable results.

        Returns:
            Number of stored opportunities.
        """

        items = tuple(
            results
        )

        if not items:
            return 0

        stored = 0

        for result in items:
            self._validate_result(
                result
            )

            if not result.is_profitable:
                continue

            await self._save_without_commit(
                result
            )

            stored += 1

        if stored:
            await self._database.commit()

        return stored

    async def exists(
        self,
        result: NetProfitResult,
    ) -> bool:
        """
        Check whether an equivalent opportunity exists.
        """

        self._validate_result(
            result
        )

        opportunity = result.opportunity

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
            opportunity.chain_id,
            opportunity.base_symbol,
            opportunity.target_symbol,
            opportunity.buy_aggregator,
            opportunity.sell_aggregator,
            str(
                opportunity.amount_usdt
            ),
            str(
                result.net_profit_usdt
            ),
        )

        return row is not None

    async def count(
        self,
    ) -> int:
        """
        Return number of stored opportunities.
        """

        row = await self._database.fetch_one(
            """
            SELECT COUNT(*)
            FROM opportunities
            """
        )

        if row is None:
            return 0

        # SQLiteDatabase returns tuple-like rows.
        return int(
            row[0]
        )

    async def store(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Legacy compatibility alias for save().
        """

        await self.save(
            result
        )

    @staticmethod
    def _validate_result(
        result: NetProfitResult,
    ) -> None:
        """
        Validate repository input.
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
