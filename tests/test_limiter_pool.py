"""
Tests for AggregatorLimiterPool.
"""

import pytest

from aggregators.limiter_pool import AggregatorLimiterPool
from aggregators.rate_limiter import RateLimiter


def create_limiter(
    standard_interval: float = 1.2,
    max_interval: float = 30.0,
) -> RateLimiter:
    """Create a test limiter."""

    return RateLimiter(
        standard_interval=standard_interval,
        max_interval=max_interval,
        backoff_multiplier=1.5,
        requests_per_minute=50,
    )


def create_pool() -> AggregatorLimiterPool:
    """Create a pool with independent test limiters."""

    return AggregatorLimiterPool(
        {
            "1inch": create_limiter(),
            "0x": create_limiter(
                standard_interval=2.0
            ),
            "Uniswap": create_limiter(
                standard_interval=3.0
            ),
            "Velora": create_limiter(
                standard_interval=4.0
            ),
        }
    )


def test_pool_stores_all_limiters():
    """Pool stores every supplied limiter."""

    pool = create_pool()

    assert len(pool) == 4

    assert pool.contains("1inch")
    assert pool.contains("0x")
    assert pool.contains("Uniswap")
    assert pool.contains("Velora")


def test_pool_returns_correct_limiter():
    """Pool returns the limiter belonging to the requested aggregator."""

    pool = create_pool()

    assert (
        pool.get("1inch").standard_interval
        == 1.2
    )

    assert (
        pool.get("0x").standard_interval
        == 2.0
    )

    assert (
        pool.get("Uniswap").standard_interval
        == 3.0
    )

    assert (
        pool.get("Velora").standard_interval
        == 4.0
    )


def test_pool_returns_names():
    """Pool returns registered aggregator names."""

    pool = create_pool()

    assert pool.names() == (
        "1inch",
        "0x",
        "Uniswap",
        "Velora",
    )


def test_pool_returns_all_limiters():
    """Pool returns all registered limiters."""

    pool = create_pool()

    limiters = pool.all()

    assert len(limiters) == 4

    assert all(
        isinstance(
            limiter,
            RateLimiter,
        )
        for limiter in limiters
    )


def test_pool_rejects_duplicate_aggregator():
    """Duplicate aggregator names are rejected."""

    pool = create_pool()

    with pytest.raises(ValueError):
        pool.add(
            "1inch",
            create_limiter(),
        )


def test_pool_rejects_invalid_limiter():
    """Only RateLimiter instances are accepted."""

    pool = AggregatorLimiterPool({})

    with pytest.raises(TypeError):
        pool.add(
            "1inch",
            object(),
        )


def test_pool_rejects_empty_name():
    """Empty aggregator names are rejected."""

    pool = AggregatorLimiterPool({})

    with pytest.raises(ValueError):
        pool.add(
            "",
            create_limiter(),
        )


def test_pool_unknown_aggregator_raises():
    """Unknown aggregator names raise KeyError."""

    pool = create_pool()

    with pytest.raises(KeyError):
        pool.get("Unknown")


def test_reset_one_limiter():
    """Reset affects only the selected aggregator."""

    pool = create_pool()

    pool.get(
        "1inch"
    ).register_rate_limit()

    pool.get(
        "0x"
    ).register_rate_limit()

    assert (
        pool.get("1inch").current_interval
        > pool.get("1inch").standard_interval
    )

    assert (
        pool.get("0x").current_interval
        > pool.get("0x").standard_interval
    )

    pool.reset("1inch")

    assert (
        pool.get("1inch").current_interval
        == pool.get("1inch").standard_interval
    )

    assert (
        pool.get("0x").current_interval
        > pool.get("0x").standard_interval
    )


def test_reset_all_limiters():
    """Reset all limiters simultaneously."""

    pool = create_pool()

    for limiter in pool.all():
        limiter.register_rate_limit()

    pool.reset_all()

    for limiter in pool.all():
        assert (
            limiter.current_interval
            == limiter.standard_interval
        )


def test_rate_limit_affects_only_selected_aggregator():
    """
    A rate-limit event for one aggregator must not affect
    another aggregator.
    """

    pool = create_pool()

    original_0x_interval = (
        pool.get("0x").current_interval
    )

    pool.register_rate_limit(
        "1inch"
    )

    assert (
        pool.get("1inch").current_interval
        > pool.get("1inch").standard_interval
    )

    assert (
        pool.get("0x").current_interval
        == original_0x_interval
    )


def test_pool_rejects_invalid_mapping():
    """Pool requires a mapping of limiters."""

    with pytest.raises(TypeError):
        AggregatorLimiterPool([])


def test_pool_rejects_non_string_name():
    """Aggregator name must be a string."""

    pool = AggregatorLimiterPool({})

    with pytest.raises(TypeError):
        pool.add(
            123,
            create_limiter(),
  )
