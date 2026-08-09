"""
Aggregator registry.

Responsibility:
    Stores initialized aggregator adapters and provides
    a single access point for the rest of the application.

Does NOT:
    - create HTTP clients;
    - read user configuration;
    - store API keys;
    - perform HTTP requests;
    - apply rate limits;
    - implement Stage 1;
    - implement Stage 2;
    - calculate arbitrage opportunities.
"""

from collections.abc import Iterable

from aggregators.aggregator_interface import AggregatorInterface


class AggregatorRegistry:
    """Registry of initialized aggregator adapters."""

    def __init__(
        self,
        aggregators: Iterable[AggregatorInterface],
    ):
        self._aggregators: dict[
            str,
            AggregatorInterface,
        ] = {}

        for aggregator in aggregators:
            self.register(aggregator)

    def register(
        self,
        aggregator: AggregatorInterface,
    ) -> None:
        """
        Register an aggregator.

        Aggregator names must be unique.
        """
        if not isinstance(
            aggregator,
            AggregatorInterface,
        ):
            raise TypeError(
                "aggregator must implement "
                "AggregatorInterface."
            )

        name = aggregator.name

        if not name:
            raise ValueError(
                "Aggregator name cannot be empty."
            )

        if name in self._aggregators:
            raise ValueError(
                f"Aggregator '{name}' is already registered."
            )

        self._aggregators[name] = aggregator

    def get(
        self,
        name: str,
    ) -> AggregatorInterface:
        """
        Return an aggregator by name.

        Raises:
            KeyError: if the aggregator is not registered.
        """
        try:
            return self._aggregators[name]
        except KeyError as error:
            raise KeyError(
                f"Aggregator '{name}' is not registered."
            ) from error

    def all(
        self,
    ) -> tuple[AggregatorInterface, ...]:
        """Return all registered aggregators."""
        return tuple(
            self._aggregators.values()
        )

    def names(
        self,
    ) -> tuple[str, ...]:
        """Return registered aggregator names."""
        return tuple(
            self._aggregators.keys()
        )

    def contains(
        self,
        name: str,
    ) -> bool:
        """Check whether an aggregator is registered."""
        return name in self._aggregators

    def official_url(
        self,
        name: str,
    ) -> str:
        """Return the official URL of an aggregator."""
        return self.get(name).official_url

    def __len__(self) -> int:
        """Return the number of registered aggregators."""
        return len(self._aggregators)
