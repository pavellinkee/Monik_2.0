"""
Tests for user configuration models.
"""

from decimal import Decimal

import pytest

from config.models import (
    AggregatorConfig,
    AggregatorRateLimitConfig,
    ScannerConfig,
    Stage1Config,
    Stage2Config,
)


def create_rate_limit():
    """Create a valid test rate-limit configuration."""

    return AggregatorRateLimitConfig(
        requests_per_minute=60,
        initial_delay_seconds=1.0,
        adaptive_delay_enabled=True,
        delay_multiplier=1.5,
        max_delay_seconds=10.0,
    )


def create_aggregator_config(
    api_key: str | None = "test-key",
):
    """Create a valid test aggregator configuration."""

    return AggregatorConfig(
        enabled=True,
        api_key=api_key,
        rate_limit=create_rate_limit(),
    )


def create_stage1_config():
    """Create the approved default Stage 1 configuration."""

    return Stage1Config(
        amount_usdt=Decimal("1000"),
        base_interval_minutes=10,
        max_interval_minutes=30,
    )


def create_stage2_config():
    """Create the approved Stage 2 configuration."""

    return Stage2Config(
        enabled=True,
        max_concurrent_checks=1,
        same_aggregator_queue_enabled=True,
        different_aggregators_parallel=True,
        priority_over_stage1=True,
    )


def test_stage1_uses_approved_defaults():
    """Stage 1 stores the approved default values."""

    config = create_stage1_config()

    assert config.amount_usdt == Decimal("1000")
    assert config.base_interval_minutes == 10
    assert config.max_interval_minutes == 30


def test_stage1_rejects_max_interval_below_base():
    """Maximum interval cannot be below the base interval."""

    config = Stage1Config(
        amount_usdt=Decimal("1000"),
        base_interval_minutes=20,
        max_interval_minutes=10,
    )

    with pytest.raises(ValueError):
        config.validate_intervals()


def test_stage1_rejects_non_positive_amount():
    """Stage 1 amount must be positive."""

    with pytest.raises(ValueError):
        Stage1Config(
            amount_usdt=Decimal("0"),
            base_interval_minutes=10,
            max_interval_minutes=30,
        )


def test_stage2_has_priority_over_stage1():
    """Stage 2 priority is enabled by default."""

    config = create_stage2_config()

    assert config.priority_over_stage1 is True


def test_stage2_queues_same_aggregator():
    """Same-aggregator Stage 2 checks use a queue."""

    config = create_stage2_config()

    assert (
        config.same_aggregator_queue_enabled
        is True
    )


def test_stage2_allows_parallel_different_aggregators():
    """Different aggregators may run in parallel."""

    config = create_stage2_config()

    assert (
        config.different_aggregators_parallel
        is True
    )


def test_rate_limit_configuration():
    """Rate-limit settings are stored correctly."""

    config = create_rate_limit()

    assert config.requests_per_minute == 60
    assert config.initial_delay_seconds == 1.0
    assert config.adaptive_delay_enabled is True
    assert config.delay_multiplier == 1.5
    assert config.max_delay_seconds == 10.0


def test_aggregator_can_have_api_key():
    """Aggregators may store an API key."""

    config = create_aggregator_config(
        api_key="secret"
    )

    assert config.api_key == "secret"


def test_aggregator_can_have_no_api_key():
    """Aggregators without authentication are supported."""

    config = create_aggregator_config(
        api_key=None
    )

    assert config.api_key is None


def test_scanner_config_requires_enabled_aggregator():
    """At least one aggregator must be enabled."""

    config = ScannerConfig(
        stage1=create_stage1_config(),
        stage2=create_stage2_config(),
        aggregators={
            "Velora": AggregatorConfig(
                enabled=False,
                api_key=None,
                rate_limit=create_rate_limit(),
            )
        },
    )

    with pytest.raises(ValueError):
        config.validate()


def test_scanner_config_accepts_multiple_aggregators():
    """Multiple aggregators can be configured."""

    config = ScannerConfig(
        stage1=create_stage1_config(),
        stage2=create_stage2_config(),
        aggregators={
            "1inch": create_aggregator_config(
                api_key="test-1inch"
            ),
            "0x": create_aggregator_config(
                api_key="test-0x"
            ),
            "Uniswap": create_aggregator_config(
                api_key="test-uniswap"
            ),
            "Velora": create_aggregator_config(
                api_key=None
            ),
        },
    )

    config.validate()

    assert len(config.aggregators) == 4


def test_unknown_fields_are_rejected():
    """Unexpected configuration fields are rejected."""

    with pytest.raises(ValueError):
        Stage1Config(
            amount_usdt=Decimal("1000"),
            base_interval_minutes=10,
            max_interval_minutes=30,
            unknown_setting=True,
        )
