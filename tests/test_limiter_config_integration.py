"""
Integration tests for configuration → limiter layer.

Tests:

    ScannerConfig
        ↓
    AggregatorLimiterManager
        ↓
    AggregatorLimiterPool
        ↓
    individual RateLimiter instances
"""

from decimal import Decimal

import pytest

from aggregators.limiter_manager import (
    AggregatorLimiterManager,
)
from config.models import (
    AggregatorConfig,
    AggregatorRateLimitConfig,
    ScannerConfig,
    Stage1Config,
    Stage2Config,
)


def create_rate_limit(
    requests_per_minute: int,
    initial_delay: float,
) -> AggregatorRateLimitConfig:
    """Create a rate-limit configuration."""

    return AggregatorRateLimitConfig(
        requests_per_minute=requests_per_minute,
        initial_delay_seconds=initial_delay,
        adaptive_delay_enabled=True,
        delay_multiplier=1.5,
        max_delay_seconds=30.0,
    )


def create_scanner_config() -> ScannerConfig:
    """Create a complete ScannerConfig."""

    return ScannerConfig(
        stage1=Stage1Config(
            amount_usdt=Decimal("1000"),
            base_interval_minutes=10,
            max_interval_minutes=30,
        ),
        stage2=Stage2Config(
            enabled=True,
            max_concurrent_checks=1,
            same_aggregator_queue_enabled=True,
            different_aggregators_parallel=True,
            priority_over_stage1=True,
        ),
        aggregators={
            "1inch": AggregatorConfig(
                enabled=True,
                api_key="test-1inch",
                rate_limit=create_rate_limit(
                    requests_per_minute=50,
                    initial_delay=1.2,
                ),
            ),
            "0x": AggregatorConfig(
                enabled=True,
                api_key="test-0x",
                rate_limit=create_rate_limit(
                    requests_per_minute=100,
                    initial_delay=0.6,
                ),
            ),
            "Uniswap": AggregatorConfig(
                enabled=True,
                api_key="test-uniswap",
                rate_limit=create_rate_limit(
                    requests_per_minute=40,
                    initial_delay=1.5,
                ),
            ),
            "Velora": AggregatorConfig(
                enabled=True,
                api_key=None,
                rate_limit=create_rate_limit(
                    requests_per_minute=30,
                    initial_delay=2.0,
                ),
            ),
        },
    )


def test_scanner_config_creates_independent_limiters():
    """
    Each configured aggregator gets an independent limiter.
    """

    config = create_scanner_config()

    config.validate()

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(
        config.aggregators
    )

    assert len(pool) == 4

    assert (
        pool.get("1inch").requests_per_minute
        == 50
    )

    assert (
        pool.get("0x").requests_per_minute
        == 100
    )

    assert (
        pool.get("Uniswap").requests_per_minute
        == 40
    )

    assert (
        pool.get("Velora").requests_per_minute
        == 30
    )


def test_one_aggregator_backoff_does_not_affect_others():
    """
    Adaptive backoff is isolated per aggregator.
    """

    config = create_scanner_config()

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(
        config.aggregators
    )

    original_0x_interval = (
        pool.get("0x").current_interval
    )

    original_uniswap_interval = (
        pool.get("Uniswap").current_interval
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

    assert (
        pool.get("Uniswap").current_interval
        == original_uniswap_interval
    )


def test_new_cycle_resets_all_aggregator_limiters():
    """
    A new scanning cycle can reset every limiter
    to its configured standard interval.
    """

    config = create_scanner_config()

    manager = AggregatorLimiterManager()

    pool = manager.create_pool(
        config.aggregators
    )

    pool.register_rate_limit("1inch")
    pool.register_rate_limit("0x")
    pool.register_rate_limit("Uniswap")

    pool.reset_all()

    for name in pool.names():
        limiter = pool.get(name)

        assert (
            limiter.current_interval
            == limiter.standard_interval
        )


def test_stage2_configuration_is_preserved_separately():
    """
    Stage 2 scheduling rules remain configuration data
    and are not mixed into the limiter itself.
    """

    config = create_scanner_config()

    assert (
        config.stage2.priority_over_stage1
        is True
    )

    assert (
        config.stage2
        .same_aggregator_queue_enabled
        is True
    )

    assert (
        config.stage2
        .different_aggregators_parallel
        is True
    )
