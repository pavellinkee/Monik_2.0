"""
Aggregator registry.

Responsibility:
    Stores the available aggregator implementations and their
    static metadata.

Does NOT:
    - create HTTP clients;
    - load user configuration;
    - store API keys;
    - create aggregator instances;
    - control rate limits;
    - run scanner stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from aggregators.aggregator_interface import AggregatorInterface
from aggregators.oneinch import OneInchAggregator
from aggregators.uniswap import UniswapAggregator
from aggregators.velora import VeloraAggregator
from aggregators.zero_x import ZeroXAggregator


@dataclass(frozen=True)
class AggregatorDefinition:
    """Static definition of one supported aggregator."""

    name: str
    implementation: Type[AggregatorInterface]
    requires_api_key: bool
    official_url: str


class AggregatorRegistry:
    """Registry of supported aggregator implementations."""

    def __init__(self) -> None:
        self._definitions: dict[
            str,
            AggregatorDefinition,
        ] = {}

        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all officially supported aggregators."""

        self.register(
            AggregatorDefinition(
                name="1inch",
                implementation=OneInchAggregator,
                requires_api_key=True,
                official_url=(
                    "https://1inch.com"
                ),
            )
        )

        self.register(
            AggregatorDefinition(
                name="0x",
                implementation=ZeroXAggregator,
                requires_api_key=True,
                official_url=(
                    "https://0x.org"
                ),
            )
        )

        self.register(
            AggregatorDefinition(
                name="Uniswap",
                implementation=UniswapAggregator,
                requires_api_key=True,
                official_url=(
                    "https://uniswap.org"
                ),
            )
        )

        self.register(
            AggregatorDefinition(
                name="Velora",
                implementation=VeloraAggregator,
                requires_api_key=False,
                official_url=(
                    "https://velora.xyz"
                ),
            )
        )

    def register(
        self,
        definition: AggregatorDefinition,
    ) -> None:
        """Register an aggregator definition."""

        if not isinstance(
            definition,
            AggregatorDefinition,
        ):
            raise TypeError(
                "definition must be an "
                "AggregatorDefinition."
            )

        if not definition.name.strip():
            raise ValueError(
                "Aggregator name cannot be empty."
            )

        if definition.name in self._definitions:
            raise ValueError(
                f"Aggregator '{definition.name}' "
                f"is already registered."
            )

        self._definitions[
            definition.name
        ] = definition

    def get(
        self,
        name: str,
    ) -> AggregatorDefinition:
        """Return a registered aggregator definition."""

        try:
            return self._definitions[name]

        except KeyError:
            raise KeyError(
                f"Unknown aggregator: '{name}'."
            ) from None

    def contains(
        self,
        name: str,
    ) -> bool:
        """Return whether an aggregator is registered."""

        return name in self._definitions

    def names(self) -> tuple[str, ...]:
        """Return registered aggregator names."""

        return tuple(
            self._definitions.keys()
        )

    def all(
        self,
    ) -> tuple[AggregatorDefinition, ...]:
        """Return all registered definitions."""

        return tuple(
            self._definitions.values()
        )

    def remove(
        self,
        name: str,
    ) -> AggregatorDefinition:
        """Remove and return an aggregator definition."""

        try:
            return self._definitions.pop(name)

        except KeyError:
            raise KeyError(
                f"Unknown aggregator: '{name}'."
            ) from None
