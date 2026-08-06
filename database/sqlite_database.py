"""
SQLite database implementation.

Responsibility:
    Implements DatabaseInterface using SQLite.
"""

from pathlib import Path
from typing import Any

import aiosqlite

from core.exceptions import DatabaseError
from database.database_interface import DatabaseInterface
from database.schema import get_schema_files


class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation."""

    def __init__(self, database_path: str):
        self._database_path = database_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open database connection."""
        try:
            self._connection = await aiosqlite.connect(self._database_path)
            await self._connection.execute("PRAGMA foreign_keys = ON;")
        except aiosqlite.Error as error:
            raise DatabaseError(
                f"Failed to connect to database: {error}"
            ) from error

    async def apply_schema(self) -> None:
        """Apply all SQL schema files."""
        assert self._connection is not None

        try:
            for sql_file in get_schema_files():
                sql = Path(sql_file).read_text(encoding="utf-8")
                await self._connection.executescript(sql)

            await self._connection.commit()

        except (OSError, aiosqlite.Error) as error:
            raise DatabaseError(
                f"Failed to apply database schema: {error}"
            ) from error

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection is None:
            return

        try:
            await self._connection.close()
        except aiosqlite.Error as error:
            raise DatabaseError(
                f"Failed to close database connection: {error}"
            ) from error
        finally:
            self._connection = None

    async def execute(self, query: str, *args: Any) -> None:
        """Execute a query safely."""
        assert self._connection is not None

        try:
            await self._connection.execute(query, args)
        except aiosqlite.Error as error:
            raise DatabaseError(
                f"Database query failed: {error}"
            ) from error

    async def fetch_one(self, query: str, *args: Any) -> Any:
        """Return one row safely."""
        assert self._connection is not None

        try:
            cursor = await self._connection.execute(query, args)
            return await cursor.fetchone()
        except aiosqlite.Error as error:
            raise DatabaseError(
                f"Database query failed: {error}"
            ) from error

    async def fetch_all(self, query: str, *args: Any) -> list[Any]:
        """Return all rows safely."""
        assert self._connection is not None

        try:
            cursor = await self._connection.execute(query, args)
            return await cursor.fetchall()
        except aiosqlite.Error as error:
            raise DatabaseError(
                f"Database query failed: {error}"
            ) from error

    async def commit(self) -> None:
        """Commit current transaction."""
        assert self._connection is not None

        try:
            await self._connection.commit()
        except aiosqlite.Error as error:
            raise DatabaseError(
                f"Failed to commit transaction: {error}"
            ) from error
