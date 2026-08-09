"""
Alert repository.

Responsibility:
    Provides database access for alert history.

Does NOT:
    - send Telegram messages;
    - decide whether an alert should be created;
    - contain Telegram API logic;
    - contain scanner business logic.
"""

from typing import Any

from database.database_interface import DatabaseInterface


class AlertRepository:
    """Repository for alert history."""

    def __init__(self, database: DatabaseInterface):
        self._database = database

    async def create(
        self,
        alert_type: str,
        source: str,
        message: str,
        created_at: str,
    ) -> None:
        """Store a sent alert."""
        await self._database.execute(
            """
            INSERT INTO alert_history (
                alert_type,
                source,
                message,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            alert_type,
            source,
            message,
            created_at,
        )

    async def get_recent(
        self,
        limit: int,
    ) -> list[Any]:
        """Return recent alerts."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                alert_type,
                source,
                message,
                created_at
            FROM alert_history
            ORDER BY id DESC
            LIMIT ?
            """,
            limit,
        )

    async def find_recent_duplicate(
        self,
        alert_type: str,
        source: str,
        message: str,
        created_after: str,
    ) -> Any:
        """
        Find a matching alert created after the specified timestamp.
        """
        return await self._database.fetch_one(
            """
            SELECT
                id,
                alert_type,
                source,
                message,
                created_at
            FROM alert_history
            WHERE alert_type = ?
              AND source = ?
              AND message = ?
              AND created_at >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            alert_type,
            source,
            message,
            created_after,
        )

    async def delete_older_than(
        self,
        created_at: str,
    ) -> None:
        """Delete alerts older than the specified timestamp."""
        await self._database.execute(
            """
            DELETE FROM alert_history
            WHERE created_at < ?
            """,
            created_at,
        )
