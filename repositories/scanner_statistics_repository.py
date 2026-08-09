"""
Scanner statistics repository.

Responsibility:
    Provides database access for cumulative scanner statistics.

Does NOT:
    - run scanner cycles;
    - calculate opportunities;
    - control scheduling;
    - contain business logic.
"""

from typing import Any

from database.database_interface import DatabaseInterface


class ScannerStatisticsRepository:
    """Repository for cumulative scanner statistics."""

    def __init__(self, database: DatabaseInterface):
        self._database = database

    async def get(self) -> Any:
        """Return current scanner statistics."""
        return await self._database.fetch_one(
            """
            SELECT
                id,
                scan_cycles,
                quotes_requested,
                opportunities_found,
                opportunities_validated
            FROM scanner_statistics
            WHERE id = 1
            """
        )

    async def increment_scan_cycles(self) -> None:
        """Increment the number of completed scan cycles."""
        await self._database.execute(
            """
            UPDATE scanner_statistics
            SET scan_cycles = scan_cycles + 1
            WHERE id = 1
            """
        )

    async def increment_quotes_requested(
        self,
        amount: int = 1,
    ) -> None:
        """Increment the number of requested quotes."""
        await self._database.execute(
            """
            UPDATE scanner_statistics
            SET quotes_requested = quotes_requested + ?
            WHERE id = 1
            """,
            amount,
        )

    async def increment_opportunities_found(
        self,
        amount: int = 1,
    ) -> None:
        """Increment the number of found opportunities."""
        await self._database.execute(
            """
            UPDATE scanner_statistics
            SET opportunities_found = opportunities_found + ?
            WHERE id = 1
            """,
            amount,
        )

    async def increment_opportunities_validated(
        self,
        amount: int = 1,
    ) -> None:
        """Increment the number of validated opportunities."""
        await self._database.execute(
            """
            UPDATE scanner_statistics
            SET opportunities_validated = opportunities_validated + ?
            WHERE id = 1
            """,
            amount,
        )
