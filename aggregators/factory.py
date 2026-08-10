"""
Aggregator factory.

Responsibility:
    Creates configured aggregator adapter instances.

Does NOT:
    - make API requests;
    - control rate limits;
    - control request queues;
    - run scanner stages;
    - calculate arbitrage;
    - send Telegram messages.
"""

from __future__ import annotations

from typing import Any

from aggregators.aggregator_interface import AggregatorInterface
from aggregators.errors import (
    AggregatorConfigurationError,
)
from aggregators.http_client_manager import (
    HttpClientManager,
)
from aggregators.registry import (
    AggregatorRegistry,
)


class AggregatorFactory:
    """Creates configured aggregator adapters."""

    def __init__(
        self,
        http_client_manager: HttpClientManager,
        registry: AggregatorRegistry | None = None,
    ):
        self._http_client_manager = (
            http_client_manager
        )

        self._registry = (
            registry
            if registry is not None
            else AggregatorRegistry()
        )

    @property
    def registry(self) -> AggregatorRegistry:
        """Return the aggregator registry."""

        return self._registry

    @property
    def http_client_manager(
        self,
    ) -> HttpClientManager:
        """Return the HTTP client manager."""

        return self._http_client_manager

    def create(
        self,
        name: str,
        config: Any,
    ) -> AggregatorInterface:
        """
        Create one configured aggregator.

        Args:
            name:
                Internal aggregator identifier.

            config:
                AggregatorConfig-compatible object.
        """

        definition = self._registry.get(name)

        enabled = getattr(
            config,
            "enabled",
            None,
        )

        if enabled is None:
            raise AggregatorConfigurationError(
                f"Aggregator '{name}' configuration "
                f"does not contain 'enabled'."
            )

        if not enabled:
            raise AggregatorConfigurationError(
                f"Aggregator '{name}' is disabled."
            )

        api_key = getattr(
            config,
            "api_key",
            None,
        )

        if definition.requires_api_key:
            if not api_key:
                raise AggregatorConfigurationError(
                    f"Aggregator '{name}' requires "
                    f"an API key."
                )

        client = (
            self._http_client_manager.get_or_create(
                name
            )
        )

        implementation = (
            definition.implementation
        )

        if definition.requires_api_key:
            return implementation(
                http_client=client,
                api_key=api_key,
            )

        return implementation(
            http_client=client,
        )

    def create_enabled(
        self,
        aggregators: dict[
            str,
            Any,
        ],
    ) -> dict[
        str,
        AggregatorInterface,
    ]:
        """
        Create all enabled aggregators.

        Disabled aggregators are skipped.
        """

        if not isinstance(
            aggregators,
            dict,
        ):
            raise TypeError(
                "aggregators must be a dictionary."
            )

        result: dict[
            str,
            AggregatorInterface,
        ] = {}

        for name, config in aggregators.items():
            if not self._registry.contains(
                name
            ):
                raise AggregatorConfigurationError(
                    f"Unknown aggregator: '{name}'."
                )

            enabled = getattr(
                config,
                "enabled",
                None,
            )

            if enabled:
                result[name] = self.create(
                    name,
                    config,
                )

        if not result:
            raise AggregatorConfigurationError(
                "No enabled aggregators were created."
            )

        return result
