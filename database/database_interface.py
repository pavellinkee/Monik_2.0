"""
Database interface.

Responsibility:
    Defines the common interface for all database implementations.

Does NOT:
    - contain SQLite-specific logic;
    - execute SQL queries;
    - contain business logic.
"""

from abc import ABC, abstractmethod
from typing import Any


class DatabaseInterface(ABC):
    """Common database interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Open database connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""

    @abstractmethod
    async def execute(self, query: str, *args: Any) -> None:
        """Execute a query without returning rows."""

    @abstractmethod
    async def fetch_one(self, query: str, *args: Any) -> Any:
        """Return a single row."""

    @abstractmethod
    async def fetch_all(self, query: str, *args: Any) -> list[Any]:
        """Return all rows."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit current transaction."""
