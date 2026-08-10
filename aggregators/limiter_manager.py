"""
Aggregator limiter manager.

Responsibility:
    Builds an AggregatorLimiterPool from user configuration.

Does NOT:
    - make HTTP requests;
    - create aggregator adapters;
    - manage Stage 1;
    - manage Stage 2;
    - decide request priority.

This component connects the configuration layer with
the rate-limiting layer.
"""

from typing import Any

from aggregators.limiter_pool import (
    AggregatorLimiterPool,
)
from aggregators.rate_limiter_factory import (
    RateLimiterFactory,
)


class AggregatorLimiterManager:
    """
    Creates and manages the limiter pool for aggregators.
    """

    def __init__(
        self,
        factory: RateLimiterFactory | None = None,
    ):
        self._factory = (
            factory
            if factory is not None
            else RateLimiterFactory()
        )

    def create_pool(
        self,
        config: dict[str, Any],
    ) -> AggregatorLimiterPool:
        """
        Create a limiter pool from aggregator configuration.

        Disabled aggregators are skipped.
        """

        limiters = self._factory.create(
            config
        )

        return AggregatorLimiterPool(
            limiters
        )

    def create_one(
        self,
        aggregator_name: str,
        config: Any,
    ):
        """
        Create a single limiter.

        This is useful when a component needs only one
        aggregator's limiter.
        """

        return self._factory.create_one(
            aggregator_name,
            config,
        )
