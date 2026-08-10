"""
Tests for AggregatorQueuePool.
"""

import pytest

from aggregators.queue_pool import (
    AggregatorQueuePool,
)
from aggregators.rate_limiter import (
    RateLimiter,
)
from aggregators.request_queue import (
    AggregatorRequestQueue,
)


def create_limiter(
    interval: float = 0.01,
) -> RateLimiter:
    """Create a test limiter."""

    return RateLimiter(
        standard_interval=interval,
        max_interval=1.0,
        backoff_multiplier=1.5,
    )


def create_queue() -> AggregatorRequestQueue:
    """Create a test request queue."""

    return AggregatorRequestQueue(
        rate_limiter=create_limiter()
    )


def create_pool() -> AggregatorQueuePool:
    """Create a test queue pool."""

    return AggregatorQueuePool(
        {
            "1inch": create_queue(),
            "0x": create_queue(),
            "Uniswap": create_queue(),
            "Velora": create_queue(),
        }
    )


def test_pool_stores_all_queues():
    """Pool stores every configured queue."""

    pool = create_pool()

    assert len(pool) == 4

    assert pool.contains("1inch")
    assert pool.contains("0x")
    assert pool.contains("Uniswap")
    assert pool.contains("Velora")


def test_pool_returns_correct_queue():
    """Pool returns the correct queue."""

    pool = create_pool()

    assert isinstance(
        pool.get("1inch"),
        AggregatorRequestQueue,
    )

    assert isinstance(
        pool.get("Velora"),
        AggregatorRequestQueue,
    )


def test_pool_returns_names():
    """Pool returns queue names in insertion order."""

    pool = create_pool()

    assert pool.names() == (
        "1inch",
        "0x",
        "Uniswap",
        "Velora",
    )


def test_pool_returns_all_queues():
    """Pool returns all registered queues."""

    pool = create_pool()

    queues = pool.all()

    assert len(queues) == 4

    assert all(
        isinstance(
            queue,
            AggregatorRequestQueue,
        )
        for queue in queues
    )


def test_pool_rejects_duplicate_queue():
    """Duplicate aggregator names are rejected."""

    pool = create_pool()

    with pytest.raises(ValueError):
        pool.add(
            "1inch",
            create_queue(),
        )


def test_pool_rejects_invalid_queue():
    """Only AggregatorRequestQueue objects are accepted."""

    pool = AggregatorQueuePool({})

    with pytest.raises(TypeError):
        pool.add(
            "1inch",
            object(),
        )


def test_pool_rejects_empty_name():
    """Empty aggregator names are rejected."""

    pool = AggregatorQueuePool({})

    with pytest.raises(ValueError):
        pool.add(
            "",
            create_queue(),
        )


def test_pool_rejects_non_string_name():
    """Aggregator name must be a string."""

    pool = AggregatorQueuePool({})

    with pytest.raises(TypeError):
        pool.add(
            123,
            create_queue(),
        )


def test_unknown_aggregator_raises():
    """Unknown aggregators raise KeyError."""

    pool = create_pool()

    with pytest.raises(KeyError):
        pool.get("Unknown")


def test_remove_returns_queue():
    """A queue can be removed."""

    pool = create_pool()

    queue = pool.remove("1inch")

    assert isinstance(
        queue,
        AggregatorRequestQueue,
    )

    assert not pool.contains("1inch")
    assert len(pool) == 3


def test_remove_unknown_aggregator_raises():
    """Removing an unknown aggregator raises KeyError."""

    pool = create_pool()

    with pytest.raises(KeyError):
        pool.remove("Unknown")


def test_from_limiters_creates_independent_queues():
    """
    Every limiter receives its own queue.
    """

    limiters = {
        "1inch": create_limiter(),
        "0x": create_limiter(),
        "Velora": create_limiter(),
    }

    pool = AggregatorQueuePool.from_limiters(
        limiters
    )

    assert len(pool) == 3

    assert pool.contains("1inch")
    assert pool.contains("0x")
    assert pool.contains("Velora")

    assert (
        pool.get("1inch")
        is not pool.get("0x")
    )


def test_from_limiters_reuses_limiter_instances():
    """Queues reuse the supplied limiter objects."""

    limiter = create_limiter()

    pool = AggregatorQueuePool.from_limiters(
        {
            "1inch": limiter,
        }
    )

    queue = pool.get("1inch")

    assert queue._rate_limiter is limiter


def test_from_limiters_rejects_invalid_limiter():
    """Invalid limiter objects are rejected."""

    with pytest.raises(TypeError):
        AggregatorQueuePool.from_limiters(
            {
                "1inch": object(),
            }
        )


def test_from_limiter_pool_uses_existing_limiters():
    """
    Creating queues from a limiter pool preserves
    the original limiter instances.
    """

    from aggregators.limiter_pool import (
        AggregatorLimiterPool,
    )

    limiter = create_limiter()

    limiter_pool = AggregatorLimiterPool(
        {
            "1inch": limiter,
        }
    )

    queue_pool = (
        AggregatorQueuePool.from_limiter_pool(
            limiter_pool
        )
    )

    assert queue_pool.contains("1inch")

    assert (
        queue_pool.get("1inch")._rate_limiter
        is limiter
    )


@pytest.mark.asyncio
async def test_start_all_starts_all_queues():
    """start_all starts every queue worker."""

    pool = create_pool()

    await pool.start_all()

    try:
        assert all(
            queue.is_running
            for queue in pool.all()
        )

    finally:
        await pool.stop_all()


@pytest.mark.asyncio
async def test_stop_all_stops_all_queues():
    """stop_all stops every queue worker."""

    pool = create_pool()

    await pool.start_all()
    await pool.stop_all()

    assert all(
        not queue.is_running
        for queue in pool.all()
    )
