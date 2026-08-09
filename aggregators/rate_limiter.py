"""
Aggregator rate limiter.

Responsibility:
    Controls the minimum interval between requests to one aggregator.

Features:
    - standard request interval;
    - adaptive interval;
    - maximum interval;
    - rate-limit backoff;
    - reset to standard values.

Does NOT:
    - make HTTP requests;
    - know about specific aggregators;
    - know about Stage 1 or Stage 2;
    - decide whether a request is necessary.
"""

import asyncio
import time


class RateLimiter:
    """Controls request frequency for one aggregator."""

    def __init__(
        self,
        standard_interval: float,
        max_interval: float,
        backoff_multiplier: float = 1.5,
    ):
        if standard_interval < 0:
            raise ValueError("standard_interval must be >= 0")

        if max_interval < standard_interval:
            raise ValueError(
                "max_interval must be >= standard_interval"
            )

        if backoff_multiplier <= 1:
            raise ValueError(
                "backoff_multiplier must be greater than 1"
            )

        self._standard_interval = standard_interval
        self._max_interval = max_interval
        self._backoff_multiplier = backoff_multiplier

        self._current_interval = standard_interval
        self._last_request_at: float | None = None

        self._lock = asyncio.Lock()

    @property
    def standard_interval(self) -> float:
        """Return the configured standard interval."""
        return self._standard_interval

    @property
    def current_interval(self) -> float:
        """Return the current adaptive interval."""
        return self._current_interval

    @property
    def max_interval(self) -> float:
        """Return the configured maximum interval."""
        return self._max_interval

    async def wait(self) -> None:
        """
        Wait until the next request is allowed.

        Only one request can pass through the limiter at a time.
        """
        async with self._lock:
            if self._last_request_at is None:
                self._last_request_at = time.monotonic()
                return

            elapsed = time.monotonic() - self._last_request_at
            delay = self._current_interval - elapsed

            if delay > 0:
                await asyncio.sleep(delay)

            self._last_request_at = time.monotonic()

    def register_rate_limit(self) -> None:
        """
        Increase the current interval after a rate-limit response.
        """
        new_interval = (
            self._current_interval * self._backoff_multiplier
        )

        self._current_interval = min(
            new_interval,
            self._max_interval,
        )

    def reset(self) -> None:
        """
        Reset adaptive state to standard values.

        Called when a new scanning cycle starts.
        """
        self._current_interval = self._standard_interval
        self._last_request_at = None
