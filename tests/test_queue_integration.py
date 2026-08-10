"""
Integration tests for the request queue layer.

Tests:

    ScannerConfig
        ↓
    AggregatorQueueManager
        ↓
    AggregatorLimiterPool
        ↓
    AggregatorQueuePool
        ↓
    AggregatorRequestQueue
        ↓
    RateLimiter
"""

import asyncio
from decimal import Decimal

import pytest

from aggregators.queue_manager import (
    AggregatorQueueManager,
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
) -> AggregatorRateLimitConfig:
    """Create a test rate-limit configuration."""

    standard_interval = (
        60.0 / requests_per_minute
    )

    return AggregatorRateLimitConfig(
        requests_per_minute=requests_per_minute,
        initial_delay_seconds=0.0,
        adaptive_delay_enabled=True,
        delay_multiplier=1.5,
        max_delay_seconds=max(
            5.0,
            standard_interval * 2,
        ),
    )


def create_scanner_config() -> ScannerConfig:
    """Create a complete scanner configuration."""

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
                    50
                ),
            ),
            "0x": AggregatorConfig(
                enabled=True,
                api_key="test-0x",
                rate_limit=create_rate_limit(
                    100
                ),
            ),
            "Uniswap": AggregatorConfig(
                enabled=True,
                api_key="test-uniswap",
                rate_limit=create_rate_limit(
                    40
                ),
            ),
            "Velora": AggregatorConfig(
                enabled=True,
                api_key=None,
                rate_limit=create_rate_limit(
                    30
                ),
            ),
        },
    )


@pytest.mark.asyncio
async def test_configuration_creates_complete_queue_layer():
    """
    Complete configuration creates independent queues
    for all enabled aggregators.
    """

    config = create_scanner_config()

    config.validate()

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        config.aggregators
    )

    assert len(pool) == 4

    assert pool.contains("1inch")
    assert pool.contains("0x")
    assert pool.contains("Uniswap")
    assert pool.contains("Velora")

    await pool.stop_all()


@pytest.mark.asyncio
async def test_different_aggregators_have_independent_queues():
    """
    Different aggregators use different queue instances.
    """

    config = create_scanner_config()

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        config.aggregators
    )

    assert (
        pool.get("1inch")
        is not pool.get("0x")
    )

    assert (
        pool.get("1inch")
        is not pool.get("Uniswap")
    )

    assert (
        pool.get("0x")
        is not pool.get("Velora")
    )

    await pool.stop_all()


@pytest.mark.asyncio
async def test_stage2_priority_survives_full_queue_pipeline():
    """
    Stage 2 priority works through the complete queue layer.
    """

    config = create_scanner_config()

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        config.aggregators
    )

    queue = pool.get("1inch")

    await queue.start()

    processed: list[str] = []

    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def running_stage1():
        processed.append("stage1-running")

        first_started.set()

        await release_first.wait()

        processed.append("stage1-finished")

        return "first"

    async def waiting_stage1():
        processed.append("stage1-second")

        return "second"

    async def waiting_stage2():
        processed.append("stage2")

        return "stage2"

    first_task = asyncio.create_task(
        queue.submit(
            running_stage1,
            stage=1,
        )
    )

    await first_started.wait()

    second_task = asyncio.create_task(
        queue.submit(
            waiting_stage1,
            stage=1,
        )
    )

    stage2_task = asyncio.create_task(
        queue.submit(
            waiting_stage2,
            stage=2,
        )
    )

    await asyncio.sleep(0)

    release_first.set()

    await asyncio.gather(
        first_task,
        second_task,
        stage2_task,
    )

    await pool.stop_all()

    assert processed == [
        "stage1-running",
        "stage1-finished",
        "stage2",
        "stage1-second",
    ]


@pytest.mark.asyncio
async def test_different_aggregators_can_process_in_parallel():
    """
    Different aggregator queues can execute independently.
    """

    config = create_scanner_config()

    manager = AggregatorQueueManager()

    pool = manager.create_pool(
        config.aggregators
    )

    queue_1inch = pool.get("1inch")
    queue_0x = pool.get("0x")

    started_1inch = asyncio.Event()
    started_0x = asyncio.Event()

    release = asyncio.Event()

    async def request_1inch():
        started_1inch.set()

        await release.wait()

        return "1inch"

    async def request_0x():
        started_0x.set()

        await release.wait()

        return "0x"

    task_1inch = asyncio.create_task(
        queue_1inch.submit(
            request_1inch,
            stage=2,
        )
    )

    task_0x = asyncio.create_task(
        queue_0x.submit(
            request_0x,
            stage=2,
        )
    )

    await asyncio.wait_for(
        asyncio.gather(
            started_1inch.wait(),
            started_0x.wait(),
        ),
        timeout=1.0,
    )

    assert started_1inch.is_set()
    assert started_0x.is_set()

    release.set()

    results = await asyncio.gather(
        task_1inch,
        task_0x,
    )

    await pool.stop_all()

    assert results == [
        "1inch",
        "0x",
    ]
