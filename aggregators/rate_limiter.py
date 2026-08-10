"""
Aggregator rate limiter.

Responsibility:
    Controls the minimum interval between requests to one aggregator.

Features:
    - standard request interval;
    - requests-per-minute protection;
    - adaptive interval;
    - maximum interval;
    - rate-limit backoff;
    - optional Retry-After support;
    - reset to standard values;
    - backward-compatible constructor aliases.

Does NOT:
    - make HTTP requests;
    - know about specific aggregators;
    - know about Stage 1 or Stage 2;
    - decide whether a request is necessary;
    - manage request priority between stages.
"""

import asyncio
import time


class RateLimiter:
    """Controls request frequency for one aggregator."""

    def __init__(
        self,
        standard_interval: float | None = None,
        max_interval: float | None = None,
        backoff_multiplier: float | None = None,
        requests_per_minute: int | None = None,
        *,
        initial_delay_seconds: float | None = None,
        max_delay_seconds: float | None = None,
        delay_multiplier: float | None = None,
    ):
        """
        Initialize the rate limiter.

        Preferred API:
            standard_interval
            max_interval
            backoff_multiplier
            requests_per_minute

        Backward-compatible API:
            initial_delay_seconds
            max_delay_seconds
            delay_multiplier

        The backward-compatible names are intentionally supported because
        existing modules and tests may still use the previous interface.
        """

        # ------------------------------------------------------------
        # Backward-compatible constructor aliases
        # ------------------------------------------------------------

        if initial_delay_seconds is not None:
            if standard_interval is not None:
                raise TypeError(
                    "Specify only one of "
                    "standard_interval and initial_delay_seconds."
                )

            standard_interval = initial_delay_seconds

        if max_delay_seconds is not None:
            if max_interval is not None:
                raise TypeError(
                    "Specify only one of "
                    "max_interval and max_delay_seconds."
                )

            max_interval = max_delay_seconds

        if delay_multiplier is not None:
            if backoff_multiplier is not None:
                raise TypeError(
                    "Specify only one of "
                    "backoff_multiplier and delay_multiplier."
                )

            backoff_multiplier = delay_multiplier

        # ------------------------------------------------------------
        # Required arguments
        # ------------------------------------------------------------

        if standard_interval is None:
            raise TypeError(
                "standard_interval is required."
            )

        if max_interval is None:
            raise TypeError(
                "max_interval is required."
            )

        if backoff_multiplier is None:
            backoff_multiplier = 1.5

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        if standard_interval < 0:
            raise ValueError(
                "standard_interval must be >= 0"
            )

        if max_interval < standard_interval:
            raise ValueError(
                "max_interval must be >= standard_interval"
            )

        if backoff_multiplier <= 1:
            raise ValueError(
                "backoff_multiplier must be greater than 1"
            )

        if requests_per_minute is not None:
            if requests_per_minute <= 0:
                raise ValueError(
                    "requests_per_minute must be greater than 0"
                )

            rpm_interval = 60.0 / requests_per_minute

            standard_interval = max(
                standard_interval,
                rpm_interval,
            )

            if max_interval < standard_interval:
                raise ValueError(
                    "max_interval must be >= the effective "
                    "standard interval"
                )

        # ------------------------------------------------------------
        # Internal state
        # ------------------------------------------------------------

        self._standard_interval = standard_interval
        self._max_interval = max_interval
        self._backoff_multiplier = backoff_multiplier
        self._requests_per_minute = requests_per_minute

        self._current_interval = standard_interval
        self._last_request_at: float | None = None

        self._lock = asyncio.Lock()

    @property
    def standard_interval(self) -> float:
        """Return the effective standard interval."""

        return self._standard_interval

    @property
    def current_interval(self) -> float:
        """Return the current adaptive interval."""

        return self._current_interval

    @property
    def max_interval(self) -> float:
        """Return the configured maximum interval."""

        return self._max_interval

    @property
    def requests_per_minute(self) -> int | None:
        """Return the configured RPM limit."""

        return self._requests_per_minute

    async def wait(self) -> None:
        """
        Wait until the next request is allowed.

        Only one request can pass through the limiter at a time.

        The lock is intentionally held while waiting. This guarantees
        that concurrent callers cannot pass the limiter simultaneously.
        """

        async with self._lock:
            if self._last_request_at is None:
                self._last_request_at = time.monotonic()
                return

            elapsed = (
                time.monotonic()
                - self._last_request_at
            )

            delay = (
                self._current_interval
                - elapsed
            )

            if delay > 0:
                await asyncio.sleep(delay)

            self._last_request_at = time.monotonic()

    def register_rate_limit(
        self,
        retry_after: float | None = None,
    ) -> None:
        """
        Increase the current interval after a rate-limit response.

        If retry_after is provided, it is treated as an additional
        lower bound for the next interval.

        The resulting interval can never exceed max_interval.
        """

        new_interval = (
            self._current_interval
            * self._backoff_multiplier
        )

        if retry_after is not None:
            if retry_after < 0:
                raise ValueError(
                    "retry_after must be >= 0"
                )

            new_interval = max(
                new_interval,
                retry_after,
            )

        self._current_interval = min(
            new_interval,
            self._max_interval,
        )

    def reset(self) -> None:
        """
        Reset adaptive state to standard values.

        The next request will therefore use the standard interval.
        """

        self._current_interval = (
            self._standard_interval
        )

        self._last_request_at = None
