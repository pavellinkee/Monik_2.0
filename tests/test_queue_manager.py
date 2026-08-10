"""
Tests for AggregatorQueueManager.
"""

import pytest

from aggregators.limiter_pool import (
    AggregatorLimiterPool,
)
from aggregators.queue_manager import (
    AggregatorQueueManager,
)
from aggregators.queue_pool import (
    AggregatorQueuePool,
)
from aggregators.rate_limiter import (
    RateLimiter,
)
from config.models import (
    AggregatorConfig,
    AggregatorRateLimitConfig,
)


def create_config(
    enabled: bool = True,
    requests_per_minute: int = 50,
    initial_delay: float = 0.01,
) -> AggregatorConfig:
    """Create a test aggregator configuration."""

    return AggregatorConfig(
        enabled=enabled,
        api_key=None,
        rate_limit=AggregatorRateLimitConfig(
            requests_per_minute=requests_per_minute,
            initial_delay_seconds=initial_delay,
            adaptive_delay_enabled=True,
            delay_multiplier=1.5,
            max_delay_seconds=1.0,
        ),
    )


def create_configs():
    """Create multiple test aggregator configurations."""

    return {
        "1inch": create_config(
            requests_per_minute=50,
            initial_delay=0.01,
        ),
        "0x": create_config(
            requests_per_minute=100,
            initial_delay=0.01,
        ),
        "Uniswap": create_config(
            requests_per_minute=40,
            initial_delay=0.01,
        ),
        "Velora": create_config(
            requests_per_minute=30,
            initial_delay=0.01,
        ),
    }


def test_manager_creates_queue_pool():
    """Manager creates a queue pool."""

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        create_configs()
    )

    assert isinstance(
        pool,
        AggregatorQueuePool,
    )

    assert len(pool) == 4


def test_manager_creates_queue_for_each_enabled_aggregator():
    """Every enabled aggregator receives one queue."""

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        create_configs()
    )

    assert pool.contains("1inch")
    assert pool.contains("0x")
    assert pool.contains("Uniswap")
    assert pool.contains("Velora")


def test_manager_skips_disabled_aggregator():
    """Disabled aggregators receive no queue."""

    configs = create_configs()

    configs["0x"] = create_config(
        enabled=False
    )

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        configs
    )

    assert len(pool) == 3

    assert not pool.contains("0x")


def test_manager_creates_from_existing_limiter_pool():
    """Manager can build queues from an existing limiter pool."""

    limiter_1inch = RateLimiter(
        standard_interval=0.01,
        max_interval=1.0,
    )

    limiter_0x = RateLimiter(
        standard_interval=0.01,
        max_interval=1.0,
    )

    limiter_pool = AggregatorLimiterPool(
        {
            "1inch": limiter_1inch,
            "0x": limiter_0x,
        }
    )

    manager = AggregatorQueueManager()

    queue_pool = (
        manager.create_from_limiter_pool(
            limiter_pool
        )
    )

    assert len(queue_pool) == 2

    assert (
        queue_pool
        .get("1inch")
        ._rate_limiter
        is limiter_1inch
    )

    assert (
        queue_pool
        .get("0x")
        ._rate_limiter
        is limiter_0x
    )


def test_manager_rejects_invalid_limiter_pool():
    """Invalid limiter pools are rejected."""

    manager = AggregatorQueueManager()

    with pytest.raises(TypeError):
        manager.create_from_limiter_pool(
            {}
        )


def test_manager_creates_one_queue():
    """Manager can create one aggregator queue."""

    manager = AggregatorQueueManager()

    queue = manager.create_one(
        "1inch",
        create_config(),
    )

    assert queue._rate_limiter.standard_interval == pytest.approx(
        0.01
    )


def test_manager_rejects_disabled_single_aggregator():
    """Disabled aggregators cannot create a queue."""

    manager = AggregatorQueueManager()

    with pytest.raises(ValueError):
        manager.create_one(
            "1inch",
            create_config(
                enabled=False
            ),
        )


@pytest.mark.asyncio
async def test_manager_pool_can_start_and_stop():
    """Queues created by manager can be started and stopped."""

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        create_configs()
    )

    await pool.start_all()

    try:
        assert all(
            queue.is_running
            for queue in pool.all()
        )

    finally:
        await pool.stop_all()

    assert all(
        not queue.is_running
        for queue in pool.all()
    )
