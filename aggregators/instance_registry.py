"""
Runtime aggregator instance registry.

Responsibility:
    Stores configured aggregator adapter instances.

Does NOT:
    - define supported aggregator implementations;
    - create aggregator instances;
    - create HTTP clients;
    - control rate limits;
    - control request queues;
    - run scanner stages;
    - calculate arbitrage;
    - send Telegram messages.

This registry is intentionally separate from AggregatorRegistry.

AggregatorRegistry:
    Stores static aggregator definitions.

AggregatorInstanceRegistry:
    Stores runtime-created aggregator instances.
"""

from __future__ import annotations

from collections.abc import Iterator

from aggregators.aggregator_interface import (
    AggregatorInterface,
)


class AggregatorInstanceRegistry:
    """Runtime registry of configured aggregator instances."""

    def __init__(
        self,
        instances: dict[
            str,
            AggregatorInterface,
        ]
        | None = None,
    ) -> None:
        self._instances: dict[
            str,
            AggregatorInterface,
        ] = {}

        if instances is not None:
            for name, instance in instances.items():
                self.register(
                    name,
                    instance,
                )

    def register(
        self,
        name: str,
        instance: AggregatorInterface,
    ) -> None:
        """Register one runtime aggregator instance."""

        if not isinstance(name, str):
            raise TypeError(
                "name must be a string."
            )

        if not name.strip():
            raise ValueError(
                "Aggregator name cannot be empty."
            )

        if not isinstance(
            instance,
            AggregatorInterface,
        ):
            raise TypeError(
                "instance must implement "
                "AggregatorInterface."
            )

        if name in self._instances:
            raise ValueError(
                f"Aggregator '{name}' is already "
                "registered."
            )

        self._instances[name] = instance

    def contains(
        self,
        name: str,
    ) -> bool:
        """Return whether an instance is registered."""

        return name in self._instances

    def get(
        self,
        name: str,
    ) -> AggregatorInterface | None:
        """Return an instance or None."""

        return self._instances.get(name)

    def require(
        self,
        name: str,
    ) -> AggregatorInterface:
        """Return an instance or raise KeyError."""

        try:
            return self._instances[name]
        except KeyError:
            raise KeyError(
                f"Unknown aggregator instance: '{name}'."
            ) from None

    def names(self) -> tuple[str, ...]:
        """Return registered instance names."""

        return tuple(
            self._instances.keys()
        )

    def values(
        self,
    ) -> tuple[AggregatorInterface, ...]:
        """Return all registered instances."""

        return tuple(
            self._instances.values()
        )

    def items(
        self,
    ) -> tuple[
        tuple[str, AggregatorInterface],
        ...,
    ]:
        """Return all registered name-instance pairs."""

        return tuple(
            self._instances.items()
        )

    def __contains__(
        self,
        name: object,
    ) -> bool:
        """Support the `name in registry` syntax."""

        return name in self._instances

    def __getitem__(
        self,
        name: str,
    ) -> AggregatorInterface:
        """Return an instance using dictionary syntax."""

        return self.require(name)

    def __len__(self) -> int:
        """Return the number of registered instances."""

        return len(self._instances)

    def __iter__(self) -> Iterator[str]:
        """Iterate over registered names."""

        return iter(self._instances)
