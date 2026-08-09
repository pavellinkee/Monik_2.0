"""
Health repository.

Responsibility:
    Provides database access for health history.

Does NOT:
    - perform health checks;
    - calculate health status;
    - monitor CPU or memory;
    - send Telegram messages.
"""

from typing import Any

from database.database_interface import DatabaseInterface


class HealthRepository:
    """Repository for health history."""

    def __init__(self, database: DatabaseInterface):
        self._database = database

    async def create(
        self,
        status: str,
        cpu_usage: float | None,
        memory_usage: float | None,
        created_at: str,
    ) -> None:
        """Store a health check result."""
        await self._database.execute(
            """
            INSERT INTO health_history (
                status,
                cpu_usage,
                memory_usage,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            status,
            cpu_usage,
            memory_usage,
            created_at,
        )

    async def get_recent(
        self,
        limit: int,
    ) -> list[Any]:
        """Return recent health checks."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                status,
                cpu_usage,
                memory_usage,
                created_at
            FROM health_history
            ORDER BY id DESC
            LIMIT ?
            """,
            limit,
        )

    async def get_latest(self) -> Any:
        """Return the latest health check."""
        return await self._database.fetch_one(
            """
            SELECT
                id,
                status,
                cpu_usage,
                memory_usage,
                created_at
            FROM health_history
            ORDER BY id DESC
            LIMIT 1
            """
        )

    async def delete_older_than(
        self,
        created_at: str,
    ) -> None:
        """Delete health records older than the specified timestamp."""
        await self._database.execute(
            """
            DELETE FROM health_history
            WHERE created_at < ?
            """,
            created_at,
        )
