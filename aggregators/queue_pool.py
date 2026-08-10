"""
Aggregator request queue pool.

Responsibility:
    Stores and provides independent request queues
    for different aggregators.

Rules:
    - Each aggregator has its own queue.
    - Each queue has its own RateLimiter.
    - Requests belonging to different aggregators do not
      share the same queue.
    - Unknown aggregators are rejected.

Does NOT:
    - make HTTP requests;
    - calculate opportunities;
    - decide scanner logic;
    - manage Telegram notifications;
    - implement rate limiting itself.
"""

from collections.abc import Mapping

from aggregators.rate_limiter import RateLimiter
from aggregators.request_queue import (
    AggregatorRequestQueue,
)


class AggregatorQueuePool:
    """
    Collection of independent request queues.

    Example:

        1inch  → Queue → RateLimiter
        0x     → Queue → RateLimiter
        Uniswap → Queue → RateLimiter
        Velora → Queue → RateLimiter
    """

    def __init__(
        self,
        queues: Mapping[
            str,
            AggregatorRequestQueue,
        ] | None = None,
    ):
        self._queues: dict[
            str,
            AggregatorRequestQueue,
        ] = {}

        if queues is not None:
            if not isinstance(
                queues,
                Mapping,
            ):
                raise TypeError(
                    "queues must be a mapping."
                )

            for name, queue in queues.items():
                self.add(
                    name,
                    queue,
                )

    def add(
        self,
        name: str,
        queue: AggregatorRequestQueue,
    ) -> None:
        """
        Add a queue for an aggregator.
        """

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "aggregator name must be a string."
            )

        if not name.strip():
            raise ValueError(
                "aggregator name cannot be empty."
            )

        if not isinstance(
            queue,
            AggregatorRequestQueue,
        ):
            raise TypeError(
                "queue must be an "
                "AggregatorRequestQueue."
            )

        if name in self._queues:
            raise ValueError(
                f"Queue for aggregator "
                f"'{name}' already exists."
            )

        self._queues[name] = queue

    def get(
        self,
        name: str,
    ) -> AggregatorRequestQueue:
        """
        Return the queue for an aggregator.
        """

        try:
            return self._queues[name]

        except KeyError:
            raise KeyError(
                f"Unknown aggregator: '{name}'."
            ) from None

    def contains(
        self,
        name: str,
    ) -> bool:
        """Return whether an aggregator is registered."""

        return name in self._queues

    def names(self) -> tuple[str, ...]:
        """
        Return registered aggregator names
        in insertion order.
        """

        return tuple(
            self._queues.keys()
        )

    def all(
        self,
    ) -> tuple[AggregatorRequestQueue, ...]:
        """Return all registered queues."""

        return tuple(
            self._queues.values()
        )

    def __len__(self) -> int:
        """Return the number of registered queues."""

        return len(self._queues)

    def remove(
        self,
        name: str,
    ) -> AggregatorRequestQueue:
        """
        Remove and return a queue.

        The queue itself is not stopped automatically.
        Lifecycle management remains explicit.
        """

        try:
            return self._queues.pop(name)

        except KeyError:
            raise KeyError(
                f"Unknown aggregator: '{name}'."
            ) from None

    async def start_all(self) -> None:
        """Start all registered queue workers."""

        for queue in self._queues.values():
            await queue.start()

    async def stop_all(self) -> None:
        """Stop all registered queue workers."""

        for queue in self._queues.values():
            await queue.stop()

    async def wait_until_empty(self) -> None:
        """
        Wait until all registered queues become empty.
        """

        for queue in self._queues.values():
            await queue.wait_until_empty()

    @classmethod
    def from_limiters(
        cls,
        limiters: Mapping[
            str,
            RateLimiter,
        ],
    ) -> "AggregatorQueuePool":
        """
        Create one independent queue for every limiter.

        This is the main bridge between the limiter layer
        and the request queue layer.
        """

        if not isinstance(
            limiters,
            Mapping,
        ):
            raise TypeError(
                "limiters must be a mapping."
            )

        pool = cls()

        for name, limiter in limiters.items():
            if not isinstance(
                limiter,
                RateLimiter,
            ):
                raise TypeError(
                    f"Limiter for '{name}' must be "
                    f"a RateLimiter."
                )

            queue = AggregatorRequestQueue(
                rate_limiter=limiter,
            )

            pool.add(
                name,
                queue,
            )

        return pool

    @classmethod
    def from_limiter_pool(
        cls,
        limiter_pool,
    ) -> "AggregatorQueuePool":
        """
        Create queues from an AggregatorLimiterPool.

        The method intentionally accepts the pool through
        its public interface instead of depending on its
        internal dictionary.
        """

        if not hasattr(
            limiter_pool,
            "names",
        ):
            raise TypeError(
                "limiter_pool must provide names()."
            )

        if not hasattr(
            limiter_pool,
            "get",
        ):
            raise TypeError(
                "limiter_pool must provide get()."
            )

        pool = cls()

        for name in limiter_pool.names():
            limiter = limiter_pool.get(name)

            if not isinstance(
                limiter,
                RateLimiter,
            ):
                raise TypeError(
                    f"Limiter for '{name}' must be "
                    f"a RateLimiter."
                )

            pool.add(
                name,
                AggregatorRequestQueue(
                    rate_limiter=limiter,
                ),
            )

        return pool
