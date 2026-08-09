"""
Diagnostic event repository.

Responsibility:
    Provides database access for diagnostic events.

Does NOT:
    - create diagnostic decisions;
    - send Telegram messages;
    - handle API requests;
    - contain business logic.
"""

from typing import Any

from database.database_interface import DatabaseInterface


class DiagnosticEventRepository:
    """Repository for diagnostic events."""

    def __init__(self, database: DatabaseInterface):
        self._database = database

    async def create(
        self,
        event_type: str,
        severity: str,
        source: str,
        message: str,
        created_at: str,
    ) -> None:
        """Create a diagnostic event."""
        await self._database.execute(
            """
            INSERT INTO diagnostic_events (
                event_type,
                severity,
                source,
                message,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            event_type,
            severity,
            source,
            message,
            created_at,
        )

    async def get_recent(
        self,
        limit: int,
    ) -> list[Any]:
        """Return the most recent diagnostic events."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                event_type,
                severity,
                source,
                message,
                created_at
            FROM diagnostic_events
            ORDER BY id DESC
            LIMIT ?
            """,
            limit,
        )

    async def get_by_severity(
        self,
        severity: str,
        limit: int,
    ) -> list[Any]:
        """Return recent events with a specific severity."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                event_type,
                severity,
                source,
                message,
                created_at
            FROM diagnostic_events
            WHERE severity = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            severity,
            limit,
        )

    async def delete_older_than(
        self,
        created_at: str,
    ) -> None:
        """Delete diagnostic events older than the specified timestamp."""
        await self._database.execute(
            """
            DELETE FROM diagnostic_events
            WHERE created_at < ?
            """,
            created_at,
        )
