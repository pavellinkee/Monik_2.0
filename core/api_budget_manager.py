"""
API budget manager.

Responsibility:
    Track and reserve request capacity independently from
    aggregator rate limiters.

The manager does NOT:
    - perform HTTP requests;
    - sleep;
    - implement rate limiting;
    - manage aggregator queues;
    - access the database.

Stage priority:
    Stage 2 reservations have priority over Stage 1.

This allows the scanner to protect capacity for opportunity
verification without bypassing the normal aggregator queues.

Compatibility:
    reserve()
    release()
    can_reserve()
    status()
"""

from __future__ import annotations

import asyncio

from models.api_budget import ApiBudgetStatus


class ApiBudgetManager:
    """
    Thread-safe asynchronous API budget manager.
    """

    def __init__(
        self,
        budgets: dict[str, int],
        *,
        stage2_reserved_capacity: int = 0,
    ) -> None:
        if not budgets:
            raise ValueError(
                "budgets must not be empty."
            )

        normalized: dict[str, int] = {}

        for aggregator, limit in budgets.items():
            if not isinstance(
                aggregator,
                str,
            ):
                raise TypeError(
                    "Aggregator name must be a string."
                )

            if not aggregator.strip():
                raise ValueError(
                    "Aggregator name cannot be empty."
                )

            if limit <= 0:
                raise ValueError(
                    "API budget must be greater than zero."
                )

            normalized[
                aggregator
            ] = int(limit)

        if stage2_reserved_capacity < 0:
            raise ValueError(
                "stage2_reserved_capacity cannot "
                "be negative."
            )

        self._limits = normalized
        self._used = {
            name: 0
            for name in normalized
        }
        self._reserved = {
            name: 0
            for name in normalized
        }

        self._stage2_reserved_capacity = (
            int(stage2_reserved_capacity)
        )

        self._lock = asyncio.Lock()

    async def can_reserve(
        self,
        aggregator: str,
        *,
        stage: int = 1,
    ) -> bool:
        """
        Check whether one request can be reserved.

        Stage 2 can consume reserved capacity.

        Stage 1 cannot consume capacity reserved for Stage 2.
        """

        self._validate_aggregator(
            aggregator
        )

        if stage not in (1, 2):
            raise ValueError(
                "stage must be either 1 or 2."
            )

        async with self._lock:
            return self._can_reserve_unlocked(
                aggregator,
                stage,
            )

    async def reserve(
        self,
        aggregator: str,
        *,
        stage: int = 1,
    ) -> bool:
        """
        Reserve one request slot.

        Returns:
            True  -> reservation succeeded
            False -> budget unavailable
        """

        self._validate_aggregator(
            aggregator
        )

        if stage not in (1, 2):
            raise ValueError(
                "stage must be either 1 or 2."
            )

        async with self._lock:
            if not self._can_reserve_unlocked(
                aggregator,
                stage,
            ):
                return False

            self._reserved[
                aggregator
            ] += 1

            return True

    async def consume_reserved(
        self,
        aggregator: str,
    ) -> None:
        """
        Convert one reservation into a used request.
        """

        self._validate_aggregator(
            aggregator
        )

        async with self._lock:
            if self._reserved[
                aggregator
            ] <= 0:
                raise ValueError(
                    "No reservation exists for "
                    f"'{aggregator}'."
                )

            self._reserved[
                aggregator
            ] -= 1

            self._used[
                aggregator
            ] += 1

    async def release(
        self,
        aggregator: str,
    ) -> None:
        """
        Release an unused reservation.
        """

        self._validate_aggregator(
            aggregator
        )

        async with self._lock:
            if self._reserved[
                aggregator
            ] <= 0:
                raise ValueError(
                    "No reservation exists for "
                    f"'{aggregator}'."
                )

            self._reserved[
                aggregator
            ] -= 1

    async def reset(
        self,
        aggregator: str | None = None,
    ) -> None:
        """
        Reset usage and reservations.

        Intended for a new API-budget window.
        """

        async with self._lock:
            if aggregator is None:
                names = tuple(
                    self._limits
                )
            else:
                self._validate_aggregator(
                    aggregator
                )
                names = (aggregator,)

            for name in names:
                self._used[name] = 0
                self._reserved[name] = 0

    async def status(
        self,
        aggregator: str,
    ) -> ApiBudgetStatus:
        """
        Return an immutable budget snapshot.
        """

        self._validate_aggregator(
            aggregator
        )

        async with self._lock:
            return ApiBudgetStatus(
                aggregator=aggregator,
                limit=self._limits[
                    aggregator
                ],
                used=self._used[
                    aggregator
                ],
                reserved=self._reserved[
                    aggregator
                ],
            )

    async def statuses(
        self,
    ) -> tuple[ApiBudgetStatus, ...]:
        """
        Return all budget snapshots.
        """

        async with self._lock:
            return tuple(
                ApiBudgetStatus(
                    aggregator=name,
                    limit=self._limits[name],
                    used=self._used[name],
                    reserved=self._reserved[name],
                )
                for name in self._limits
            )

    def _can_reserve_unlocked(
        self,
        aggregator: str,
        stage: int,
    ) -> bool:
        used = self._used[
            aggregator
        ]

        reserved = self._reserved[
            aggregator
        ]

        limit = self._limits[
            aggregator
        ]

        available = (
            limit
            - used
            - reserved
        )

        if available <= 0:
            return False

        if stage == 2:
            return True

        total_free_after_reservation = (
            available - 1
        )

        return (
            total_free_after_reservation
            >= self._stage2_reserved_capacity
        )

    def _validate_aggregator(
        self,
        aggregator: str,
    ) -> None:
        if not isinstance(
            aggregator,
            str,
        ):
            raise TypeError(
                "aggregator must be a string."
            )

        if aggregator not in self._limits:
            raise KeyError(
                f"Unknown aggregator: {aggregator}"
            )
