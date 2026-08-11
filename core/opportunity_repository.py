"""
Opportunity repository contract.

Responsibility:
    Define the persistence contract for validated profitable
    arbitrage opportunities.

The implementation is intentionally separated from the
domain pipeline.

Possible implementations:
    - SQLite;
    - PostgreSQL;
    - another SQL backend.

The scanner must not depend on a specific database engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from models.net_profit import NetProfitResult


class OpportunityRepository(ABC):
    """
    Abstract persistence interface for profitable opportunities.
    """

    @abstractmethod
    async def save(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Persist one profitable opportunity.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_many(
        self,
        results: Iterable[NetProfitResult],
    ) -> int:
        """
        Persist multiple profitable opportunities.

        Returns:
            Number of stored opportunities.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        result: NetProfitResult,
    ) -> bool:
        """
        Check whether an equivalent opportunity already exists.
        """
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        """
        Return total number of stored opportunities.
        """
        raise NotImplementedError

    async def store(
        self,
        result: NetProfitResult,
    ) -> None:
        """
        Legacy compatibility alias for save().
        """
        await self.save(result)
