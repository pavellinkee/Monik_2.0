"""
Aggregator statistics repository.

Responsibility:
    Provides database access for aggregator statistics.

Does NOT:
    - make API requests;
    - calculate trading opportunities;
    - enforce rate limits;
    - contain scanner logic.
"""

from typing import Any

from database.database_interface import DatabaseInterface


class AggregatorStatisticsRepository:
    """Repository for aggregator statistics."""

    def __init__(self, database: DatabaseInterface):
        self._database = database

    async def get(
        self,
        aggregator: str,
        network: str,
    ) -> Any:
        """Return statistics for an aggregator on a network."""
        return await self._database.fetch_one(
            """
            SELECT
                id,
                aggregator,
                network,
                requests,
                successful_requests,
                failed_requests,
                rate_limit_hits,
                opportunities_found
            FROM aggregator_statistics
            WHERE aggregator = ?
              AND network = ?
            """,
            aggregator,
            network,
        )

    async def get_all(self) -> list[Any]:
        """Return all aggregator statistics."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                aggregator,
                network,
                requests,
                successful_requests,
                failed_requests,
                rate_limit_hits,
                opportunities_found
            FROM aggregator_statistics
            ORDER BY aggregator ASC, network ASC
            """
        )

    async def increment_requests(
        self,
        aggregator: str,
        network: str,
    ) -> None:
        """Increment total request counter."""
        await self._database.execute(
            """
            UPDATE aggregator_statistics
            SET requests = requests + 1
            WHERE aggregator = ?
              AND network = ?
            """,
            aggregator,
            network,
        )

    async def increment_successful_requests(
        self,
        aggregator: str,
        network: str,
    ) -> None:
        """Increment successful request counter."""
        await self._database.execute(
            """
            UPDATE aggregator_statistics
            SET successful_requests = successful_requests + 1
            WHERE aggregator = ?
              AND network = ?
            """,
            aggregator,
            network,
        )

    async def increment_failed_requests(
        self,
        aggregator: str,
        network: str,
    ) -> None:
        """Increment failed request counter."""
        await self._database.execute(
            """
            UPDATE aggregator_statistics
            SET failed_requests = failed_requests + 1
            WHERE aggregator = ?
              AND network = ?
            """,
            aggregator,
            network,
        )

    async def increment_rate_limit_hits(
        self,
        aggregator: str,
        network: str,
    ) -> None:
        """Increment rate-limit counter."""
        await self._database.execute(
            """
            UPDATE aggregator_statistics
            SET rate_limit_hits = rate_limit_hits + 1
            WHERE aggregator = ?
              AND network = ?
            """,
            aggregator,
            network,
        )

    async def increment_opportunities_found(
        self,
        aggregator: str,
        network: str,
    ) -> None:
        """Increment opportunity counter."""
        await self._database.execute(
            """
            UPDATE aggregator_statistics
            SET opportunities_found = opportunities_found + 1
            WHERE aggregator = ?
              AND network = ?
            """,
            aggregator,
            network,
        )
