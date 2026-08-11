"""
SQL opportunity repository.

Persists only validated profitable opportunities.

Compatibility:
    - OpportunityRepository contract;
    - DatabaseInterface;
    - SQLiteDatabase;
    - legacy store().
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
    SQL-backed opportunity repository.
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
        Save one profitable opportunity.
        """

        self._validate_result(
            result
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
        )

        await self._database.commit()

    async def save_many(
        self,
        results: Iterable[NetProfitResult],
    ) -> int:
        """
        Save all profitable results and commit once.
        """

        items = tuple(
            results
        )

        stored = 0

        for result in items:
            self._validate_result(
                result
            )

            if not result.is_profitable:
                continue

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
        )

        return row is not None

    async def count(
        self,
    ) -> int:
        """
        Return number of stored opportunities.

        SQLiteDatabase returns tuple-like rows.
        """

        row = await self._database.fetch_one(
            """
            SELECT COUNT(*)
            FROM opportunities
            """
        )

        if row is None:
            return 0

        return int(
            row[0]
        )

    async def store(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Legacy compatibility alias.
        """

        await self.save(
            result
        )

    @staticmethod
    def _validate_result(
        result: NetProfitResult,
    ) -> None:
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
