"""
Aggregator failover manager.

Responsibility:
    Executes a request using an ordered list of aggregator sources.

Rules:
    - Each source receives at most the configured number of attempts.
    - After the final failed attempt, the next source is tried.
    - Aggregator-specific errors are normalized by the aggregator adapter.
    - Rate-limit errors are reported to the caller.
    - Source order is preserved.

Does NOT:
    - make HTTP requests directly;
    - implement rate limiting;
    - manage request queues;
    - calculate profitability;
    - send Telegram messages.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from aggregators.errors import AggregatorError


@dataclass(frozen=True)
class FailoverSource:
    """One source available for failover."""

    name: str
    request: Callable[[], Awaitable[Any]]


class FailoverError(AggregatorError):
    """All configured sources failed."""


class FailoverManager:
    """Executes requests with automatic source failover."""

    def __init__(
        self,
        max_attempts_per_source: int = 2,
    ):
        if max_attempts_per_source < 1:
            raise ValueError(
                "max_attempts_per_source must be at least 1"
            )

        self._max_attempts_per_source = max_attempts_per_source

    @property
    def max_attempts_per_source(self) -> int:
        """Return the configured attempts per source."""
        return self._max_attempts_per_source

    async def execute(
        self,
        sources: list[FailoverSource],
    ) -> Any:
        """
        Execute a request using the configured source order.

        Each source receives up to the configured number of attempts.
        After all attempts fail, the next source is tried.
        """
        if not sources:
            raise FailoverError(
                "No failover sources are configured."
            )

        errors: list[str] = []

        for source in sources:
            for attempt in range(
                1,
                self._max_attempts_per_source + 1,
            ):
                try:
                    return await source.request()

                except Exception as error:
                    errors.append(
                        f"{source.name} "
                        f"attempt {attempt}: {error}"
                    )

        raise FailoverError(
            "All configured aggregator sources failed: "
            + "; ".join(errors)
        )
