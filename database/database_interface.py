"""
Database interface.

Responsibility:
    Defines the common interface for all database implementations.
"""

from abc import ABC, abstractmethod
from typing import Any


class DatabaseInterface(ABC):
    """Common database interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Open database connection."""

    @abstractmethod
    async def apply_schema(self) -> None:
        """Apply database schema."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""

    @abstractmethod
    async def execute(self, query: str, *args: Any) -> None:
        """Execute a query safely."""

    @abstractmethod
    async def fetch_one(self, query: str, *args: Any) -> Any:
        """Return a single row safely."""

    @abstractmethod
    async def fetch_all(self, query: str, *args: Any) -> list[Any]:
        """Return all rows safely."""

    @abstractmethod
    async def commit(self) -> None:
        """Commit current transaction."""
