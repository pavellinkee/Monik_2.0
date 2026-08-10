"""
Tests for the aggregator rate limiter.
"""

import asyncio

import pytest

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


def test_standard_interval_is_preserved():
    """Standard interval is stored correctly."""

    limiter = RateLimiter(
        standard_interval=1.2,
        max_interval=30.0,
    )

    assert limiter.standard_interval == pytest.approx(
        1.2
    )
    assert limiter.current_interval == pytest.approx(
        1.2
    )
    assert limiter.max_interval == pytest.approx(
        30.0
    )


def test_rpm_protection_cannot_be_bypassed():
    """
    RPM protection prevents an interval below 60 / RPM.
    """

    limiter = RateLimiter(
        standard_interval=0.5,
        max_interval=30.0,
        requests_per_minute=50,
    )

    assert limiter.standard_interval == pytest.approx(
        1.2
    )

    assert limiter.current_interval == pytest.approx(
        1.2
    )


def test_initial_interval_can_be_above_rpm_minimum():
    """A larger configured delay is preserved."""

    limiter = RateLimiter(
        standard_interval=2.0,
        max_interval=30.0,
        requests_per_minute=50,
    )

    assert limiter.standard_interval == pytest.approx(
        2.0
    )


def test_rate_limit_increases_interval():
    """Rate-limit response increases the interval."""

    limiter = RateLimiter(
        standard_interval=1.2,
        max_interval=30.0,
        backoff_multiplier=1.5,
    )

    limiter.register_rate_limit()

    assert limiter.current_interval == pytest.approx(
        1.8
    )


def test_rate_limit_backoff_is_capped():
    """Adaptive interval cannot exceed the maximum."""

    limiter = RateLimiter(
        standard_interval=10.0,
        max_interval=12.0,
        backoff_multiplier=2.0,
    )

    limiter.register_rate_limit()

    assert limiter.current_interval == pytest.approx(
        12.0
    )


def test_retry_after_is_respected():
    """Retry-After becomes a lower bound for the next interval."""

    limiter = RateLimiter(
        standard_interval=1.2,
        max_interval=30.0,
        backoff_multiplier=1.5,
    )

    limiter.register_rate_limit(
        retry_after=10.0
    )

    assert limiter.current_interval == pytest.approx(
        10.0
    )


def test_retry_after_cannot_exceed_maximum():
    """Retry-After is capped by max_interval."""

    limiter = RateLimiter(
        standard_interval=1.2,
        max_interval=5.0,
        backoff_multiplier=1.5,
    )

    limiter.register_rate_limit(
        retry_after=20.0
    )

    assert limiter.current_interval == pytest.approx(
        5.0
    )


def test_reset_restores_standard_interval():
    """Reset returns the limiter to its standard interval."""

    limiter = RateLimiter(
        standard_interval=1.2,
        max_interval=30.0,
        backoff_multiplier=1.5,
    )

    limiter.register_rate_limit()

    assert limiter.current_interval == pytest.approx(
        1.8
    )

    limiter.reset()

    assert limiter.current_interval == pytest.approx(
        1.2
    )


def test_reset_clears_previous_request_timestamp():
    """Reset allows the next request immediately."""

    limiter = RateLimiter(
        standard_interval=10.0,
        max_interval=30.0,
    )

    asyncio.run(
        limiter.wait()
    )

    assert limiter._last_request_at is not None

    limiter.reset()

    assert limiter._last_request_at is None


def test_invalid_standard_interval_is_rejected():
    """Negative standard interval is invalid."""

    with pytest.raises(ValueError):
        RateLimiter(
            standard_interval=-1.0,
            max_interval=10.0,
        )


def test_invalid_max_interval_is_rejected():
    """Maximum interval cannot be below standard interval."""

    with pytest.raises(ValueError):
        RateLimiter(
            standard_interval=10.0,
            max_interval=5.0,
        )


def test_invalid_backoff_multiplier_is_rejected():
    """Backoff multiplier must be greater than one."""

    with pytest.raises(ValueError):
        RateLimiter(
            standard_interval=1.0,
            max_interval=10.0,
            backoff_multiplier=1.0,
        )


def test_invalid_rpm_is_rejected():
    """RPM must be positive."""

    with pytest.raises(ValueError):
        RateLimiter(
            standard_interval=1.0,
            max_interval=10.0,
            requests_per_minute=0,
        )


def test_rpm_can_be_disabled_for_backward_compatibility():
    """RPM remains optional for existing callers."""

    limiter = RateLimiter(
        standard_interval=1.0,
        max_interval=10.0,
        requests_per_minute=None,
    )

    assert limiter.requests_per_minute is None

    assert limiter.standard_interval == pytest.approx(
        1.0
    )


@pytest.mark.asyncio
async def test_first_request_does_not_wait():
    """The first request passes immediately."""

    limiter = RateLimiter(
        standard_interval=10.0,
        max_interval=30.0,
    )

    start = asyncio.get_running_loop().time()

    await limiter.wait()

    elapsed = (
        asyncio.get_running_loop().time()
        - start
    )

    assert elapsed < 0.1


@pytest.mark.asyncio
async def test_concurrent_requests_are_serialized():
    """
    Concurrent requests cannot pass the limiter simultaneously.
    """

    limiter = RateLimiter(
        standard_interval=0.05,
        max_interval=1.0,
    )

    timestamps: list[float] = []

    async def make_request():
        await limiter.wait()

        timestamps.append(
            asyncio.get_running_loop().time()
        )

    await asyncio.gather(
        make_request(),
        make_request(),
        make_request(),
    )

    assert len(timestamps) == 3

    assert (
        timestamps[1] - timestamps[0]
        >= 0.04
    )

    assert (
        timestamps[2] - timestamps[1]
        >= 0.04
    )
