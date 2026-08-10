"""
Aggregator queue manager.

Responsibility:
    Creates and manages the request-queue pool for all
    configured aggregators.

Architecture:

    User configuration
          ↓
    Limiter Manager
          ↓
    AggregatorLimiterPool
          ↓
    Queue Manager
          ↓
    AggregatorQueuePool
          ↓
    AggregatorRequestQueue
          ↓
    RateLimiter

Does NOT:
    - make HTTP requests;
    - calculate opportunities;
    - implement scanner logic;
    - send Telegram messages;
    - decide whether Stage 1 or Stage 2 should create
      a particular request.

Stage priority is handled by AggregatorRequestQueue.
"""

from typing import Any

from aggregators.limiter_manager import (
    AggregatorLimiterManager,
)
from aggregators.limiter_pool import (
    AggregatorLimiterPool,
)
from aggregators.queue_pool import (
    AggregatorQueuePool,
)


class AggregatorQueueManager:
    """
    Creates and manages request queues for aggregators.

    The manager connects the limiter layer with the
    request-queue layer.
    """

    def __init__(
        self,
        limiter_manager: (
            AggregatorLimiterManager | None
        ) = None,
    ):
        self._limiter_manager = (
            limiter_manager
            if limiter_manager is not None
            else AggregatorLimiterManager()
        )

    def create_pool(
        self,
        config: dict[str, Any],
    ) -> AggregatorQueuePool:
        """
        Create a complete queue pool from aggregator configuration.

        Disabled aggregators are skipped automatically.

        The method creates:

            configuration
                ↓
            limiter pool
                ↓
            queue pool
        """

        limiter_pool = (
            self._limiter_manager.create_pool(
                config
            )
        )

        return self.create_from_limiter_pool(
            limiter_pool
        )

    def create_from_limiter_pool(
        self,
        limiter_pool: AggregatorLimiterPool,
    ) -> AggregatorQueuePool:
        """
        Create a queue pool from an existing limiter pool.

        Existing RateLimiter instances are reused.

        This is important because the queue must use the
        exact same limiter instance that belongs to the
        aggregator.
        """

        if not isinstance(
            limiter_pool,
            AggregatorLimiterPool,
        ):
            raise TypeError(
                "limiter_pool must be an "
                "AggregatorLimiterPool."
            )

        return AggregatorQueuePool.from_limiter_pool(
            limiter_pool
        )

    def create_one(
        self,
        aggregator_name: str,
        config: Any,
    ):
        """
        Create one request queue for one aggregator.

        This is useful when a component needs only one
        aggregator queue.
        """

        limiter = (
            self._limiter_manager.create_one(
                aggregator_name,
                config,
            )
        )

        from aggregators.request_queue import (
            AggregatorRequestQueue,
        )

        return AggregatorRequestQueue(
            rate_limiter=limiter
        )
