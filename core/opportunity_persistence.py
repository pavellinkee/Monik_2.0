"""
Opportunity persistence service.

Responsibility:
    Persist only profitable NetProfitResult objects.

The service:
    - rejects non-profitable results;
    - avoids duplicate writes when the repository supports
      existence checks;
    - delegates actual persistence to OpportunityRepository.

It does NOT:
    - calculate profit;
    - calculate gas;
    - access SQL directly;
    - send notifications.
"""

from __future__ import annotations

from collections.abc import Iterable

from core.opportunity_repository import (
    OpportunityRepository,
)
from models.net_profit import NetProfitResult


class OpportunityPersistence:
    """
    Domain-level persistence service.
    """

    def __init__(
        self,
        repository: OpportunityRepository,
    ) -> None:
        if not isinstance(
            repository,
            OpportunityRepository,
        ):
            raise TypeError(
                "repository must implement "
                "OpportunityRepository."
            )

        self._repository = repository

    async def persist(
        self,
        result: NetProfitResult,
    ) -> bool:
        """
        Persist one profitable result.

        Returns:
            True  -> stored
            False -> skipped
        """

        if not isinstance(
            result,
            NetProfitResult,
        ):
            raise TypeError(
                "result must be a NetProfitResult."
            )

        if not result.is_profitable:
            return False

        if await self._repository.exists(
            result
        ):
            return False

        await self._repository.save(
            result
        )

        return True

    async def persist_many(
        self,
        results: Iterable[NetProfitResult],
    ) -> int:
        """
        Persist profitable results.

        Duplicate and non-profitable results are skipped.
        """

        items = tuple(results)

        for result in items:
            if not isinstance(
                result,
                NetProfitResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "NetProfitResult objects."
                )

        profitable: list[
            NetProfitResult
        ] = []

        for result in items:
            if not result.is_profitable:
                continue

            if await self._repository.exists(
                result
            ):
                continue

            profitable.append(result)

        if not profitable:
            return 0

        return await self._repository.save_many(
            profitable
        )

    async def store(
        self,
        result: NetProfitResult,
    ) -> bool:
        """
        Legacy compatibility alias for persist().
        """
        return await self.persist(result)
