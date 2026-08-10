"""
Tests for AggregatorLimiterManager.
"""

from decimal import Decimal

import pytest

from aggregators.limiter_manager import (
    AggregatorLimiterManager,
)
from aggregators.limiter_pool import (
    AggregatorLimiterPool,
)
from config.models import (
    AggregatorConfig,
    AggregatorRateLimitConfig,
)


def create_rate_limit(
    requests_per_minute: int = 50,
    initial_delay: float = 1.2,
    max_delay: float = 30.0,
) -> AggregatorRateLimitConfig:
    """Create a valid rate-limit configuration."""

    return AggregatorRateLimitConfig(
        requests_per_minute=requests_per_minute,
        initial_delay_seconds=initial_delay,
        adaptive_delay_enabled=True,
        delay_multiplier=1.5,
        max_delay_seconds=max_delay,
    )


def create_aggregator(
    api_key: str | None = None,
    requests_per_minute: int = 50,
    initial_delay: float = 1.2,
) -> AggregatorConfig:
    """Create a valid aggregator configuration."""

    return AggregatorConfig(
        enabled=True,
        api_key=api_key,
        rate_limit=create_rate_limit(
            requests_per_minute=requests_per_minute,
            initial_delay=initial_delay,
        ),
    )


def test_manager_creates_pool():
    """Manager creates a limiter pool."""

    config = {
        "1inch": create_aggregator(
            api_key="test-key",
            requests_per_minute=50,
            initial_delay=1.2,
        ),
        "0x": create_aggregator(
            api_key="test-key",
            requests_per_minute=100,
            initial_delay=0.6,
        ),
        "Velora": create_aggregator(
            api_key=None,
            requests_per_minute=40,
            initial_delay=2.0,
        ),
    }

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(config)

    assert isinstance(
        pool,
        AggregatorLimiterPool,
    )

    assert len(pool) == 3


def test_manager_preserves_individual_aggregator_limits():
    """
    Each aggregator receives its own rate-limit configuration.
    """

    config = {
        "1inch": create_aggregator(
            requests_per_minute=50,
            initial_delay=1.2,
        ),
        "0x": create_aggregator(
            requests_per_minute=100,
            initial_delay=0.6,
        ),
        "Velora": create_aggregator(
            requests_per_minute=30,
            initial_delay=2.0,
        ),
    }

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(config)

    assert (
        pool.get("1inch").requests_per_minute
        == 50
    )

    assert (
        pool.get("0x").requests_per_minute
        == 100
    )

    assert (
        pool.get("Velora").requests_per_minute
        == 30
    )

    assert (
        pool.get("1inch").standard_interval
        == pytest.approx(1.2)
    )

    assert (
        pool.get("0x").standard_interval
        == pytest.approx(0.6)
    )

    assert (
        pool.get("Velora").standard_interval
        == pytest.approx(2.0)
    )


def test_manager_skips_disabled_aggregators():
    """Disabled aggregators receive no limiter."""

    config = {
        "1inch": create_aggregator(
            requests_per_minute=50,
        ),
        "0x": AggregatorConfig(
            enabled=False,
            api_key=None,
            rate_limit=create_rate_limit(),
        ),
    }

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(config)

    assert len(pool) == 1

    assert pool.contains("1inch")
    assert not pool.contains("0x")


def test_manager_can_create_one_limiter():
    """Manager can create a limiter for one aggregator."""

    config = create_aggregator(
        requests_per_minute=50,
        initial_delay=1.2,
    )

    manager = AggregatorLimiterManager()

    limiter = manager.create_one(
        "1inch",
        config,
    )

    assert limiter.requests_per_minute == 50

    assert (
        limiter.standard_interval
        == pytest.approx(1.2)
    )


def test_manager_uses_pydantic_configuration():
    """
    Manager accepts the Pydantic configuration models
    produced by ScannerConfig.
    """

    config = {
        "1inch": create_aggregator(
            requests_per_minute=50,
        )
    }

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(config)

    assert pool.contains("1inch")


def test_manager_rejects_invalid_configuration():
    """Invalid configuration is rejected."""

    manager = AggregatorLimiterManager()

    with pytest.raises(TypeError):
        manager.create_pool(
            "invalid"
        )


def test_manager_rejects_missing_rate_limit():
    """Missing rate-limit configuration is rejected."""

    config = {
        "1inch": {
            "enabled": True,
            "api_key": "test-key",
        }
    }

    manager = AggregatorLimiterManager()

    with pytest.raises(ValueError):
        manager.create_pool(config)
