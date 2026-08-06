"""
SQLite database implementation.

Responsibility:
    Implements DatabaseInterface using SQLite.
"""

from pathlib import Path
import aiosqlite

from database.database_interface import DatabaseInterface
from database.schema import get_schema_files


class SQLiteDatabase(DatabaseInterface):
    """
    SQLite database implementation.
    """

    def __init__(self, database_path: str):
        self._database_path = database_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open database connection."""
        self._connection = await aiosqlite.connect(self._database_path)
        await self._connection.execute("PRAGMA foreign_keys = ON;")

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def execute(self, query: str, *args) -> None:
        """Execute a query."""
        assert self._connection is not None
        await self._connection.execute(query, args)

    async def fetch_one(self, query: str, *args):
        """Fetch one row."""
        assert self._connection is not None

        cursor = await self._connection.execute(query, args)
        return await cursor.fetchone()

    async def fetch_all(self, query: str, *args):
        """Fetch all rows."""
        assert self._connection is not None

        cursor = await self._connection.execute(query, args)
        return await cursor.fetchall()

    async def commit(self) -> None:
        """Commit current transaction."""
        assert self._connection is not None
        await self._connection.commit()

    async def apply_schema(self) -> None:
        """
        Apply all SQL schema files.
        """
        assert self._connection is not None

        for sql_file in get_schema_files():
            sql = Path(sql_file).read_text(encoding="utf-8")
            await self._connection.executescript(sql)

        await self._connection.commit()
