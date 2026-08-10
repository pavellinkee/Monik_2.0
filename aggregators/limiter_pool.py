"""
Aggregator limiter pool.

Responsibility:
    Stores and provides independent RateLimiter instances
    for configured aggregators.

Does NOT:
    - make HTTP requests;
    - create aggregators;
    - decide whether a request is necessary;
    - manage Stage 1;
    - manage Stage 2;
    - decide request priority.

Stage 1 and Stage 2 will use this pool to access the limiter
belonging to a specific aggregator.
"""

from collections.abc import Mapping

from aggregators.rate_limiter import RateLimiter


class AggregatorLimiterPool:
    """Stores one independent RateLimiter per aggregator."""

    def __init__(
        self,
        limiters: Mapping[str, RateLimiter],
    ):
        if not isinstance(limiters, Mapping):
            raise TypeError(
                "limiters must be a mapping."
            )

        self._limiters: dict[
            str,
            RateLimiter,
        ] = {}

        for name, limiter in limiters.items():
            self.add(
                name,
                limiter,
            )

    def add(
        self,
        aggregator_name: str,
        limiter: RateLimiter,
    ) -> None:
        """
        Add a limiter for an aggregator.

        Aggregator names must be unique.
        """

        if not isinstance(
            aggregator_name,
            str,
        ):
            raise TypeError(
                "aggregator_name must be a string."
            )

        aggregator_name = aggregator_name.strip()

        if not aggregator_name:
            raise ValueError(
                "aggregator_name cannot be empty."
            )

        if not isinstance(
            limiter,
            RateLimiter,
        ):
            raise TypeError(
                "limiter must be a RateLimiter."
            )

        if aggregator_name in self._limiters:
            raise ValueError(
                f"Limiter for '{aggregator_name}' "
                "is already registered."
            )

        self._limiters[
            aggregator_name
        ] = limiter

    def get(
        self,
        aggregator_name: str,
    ) -> RateLimiter:
        """
        Return the limiter belonging to an aggregator.

        Raises:
            KeyError:
                If the aggregator is not registered.
        """

        try:
            return self._limiters[
                aggregator_name
            ]

        except KeyError as error:
            raise KeyError(
                f"No rate limiter registered for "
                f"aggregator '{aggregator_name}'."
            ) from error

    def contains(
        self,
        aggregator_name: str,
    ) -> bool:
        """Return whether a limiter is registered."""

        return aggregator_name in self._limiters

    def names(
        self,
    ) -> tuple[str, ...]:
        """Return all registered aggregator names."""

        return tuple(
            self._limiters.keys()
        )

    def all(
        self,
    ) -> tuple[RateLimiter, ...]:
        """Return all registered limiters."""

        return tuple(
            self._limiters.values()
        )

    def reset_all(self) -> None:
        """
        Reset every registered limiter.

        Intended for the beginning of a new scanning cycle.
        """

        for limiter in self._limiters.values():
            limiter.reset()

    def reset(
        self,
        aggregator_name: str,
    ) -> None:
        """Reset one specific aggregator limiter."""

        self.get(
            aggregator_name
        ).reset()

    def register_rate_limit(
        self,
        aggregator_name: str,
        retry_after: float | None = None,
    ) -> None:
        """
        Register a rate-limit event for one aggregator.

        The adaptive delay of other aggregators is unaffected.
        """

        self.get(
            aggregator_name
        ).register_rate_limit(
            retry_after=retry_after
        )

    def __len__(self) -> int:
        """Return the number of registered limiters."""

        return len(self._limiters)
