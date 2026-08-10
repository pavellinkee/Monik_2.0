"""
Aggregator factory.

Responsibility:
    Creates configured aggregator adapter instances.

Supports:
    - the existing configuration pipeline;
    - the shared HttpClient;
    - HttpClientManager-based creation;
    - AggregatorRegistry-based implementation lookup;
    - AggregatorInstanceRegistry for created instances.

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

from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.errors import (
    AggregatorConfigurationError,
)
from aggregators.http_client import HttpClient
from aggregators.http_client_manager import (
    HttpClientManager,
)
from aggregators.instance_registry import (
    AggregatorInstanceRegistry,
)
from aggregators.registry import AggregatorRegistry


class AggregatorFactory:
    """Creates configured aggregator adapters."""

    def __init__(
        self,
        http_client: HttpClient | None = None,
        *,
        http_client_manager: (
            HttpClientManager | None
        ) = None,
        registry: AggregatorRegistry | None = None,
    ):
        if (
            http_client is None
            and http_client_manager is None
        ):
            raise ValueError(
                "Either http_client or "
                "http_client_manager must be provided."
            )

        self._http_client = http_client

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
        """Return the static aggregator registry."""

        return self._registry

    @property
    def http_client(self) -> HttpClient | None:
        """Return the shared HTTP client."""

        return self._http_client

    @property
    def http_client_manager(
        self,
    ) -> HttpClientManager | None:
        """Return the HTTP client manager."""

        return self._http_client_manager

    def _get_http_client(
        self,
        name: str,
    ) -> HttpClient:
        """Resolve the HTTP client for an aggregator."""

        if self._http_client_manager is not None:
            return self._http_client_manager.get_or_create(
                name
            )

        if self._http_client is not None:
            return self._http_client

        raise RuntimeError(
            "No HTTP client source is configured."
        )

    def _registry_contains(
        self,
        name: str,
    ) -> bool:
        """Check whether an aggregator is registered."""

        return self._registry.contains(name)

    def _registry_get(
        self,
        name: str,
    ):
        """Get an aggregator definition."""

        return self._registry.get(name)

    def _create_one(
        self,
        name: str,
        config: Any,
    ) -> AggregatorInterface:
        """Create one configured aggregator."""

        if not self._registry_contains(name):
            raise KeyError(
                f"Unknown aggregator: '{name}'."
            )

        definition = self._registry_get(name)

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

        requires_api_key = getattr(
            definition,
            "requires_api_key",
            False,
        )

        if requires_api_key and not api_key:
            raise AggregatorConfigurationError(
                f"Aggregator '{name}' requires "
                f"an API key."
            )

        http_client = self._get_http_client(
            name
        )

        implementation = getattr(
            definition,
            "implementation",
            definition,
        )

        if requires_api_key:
            return implementation(
                http_client=http_client,
                api_key=api_key,
            )

        return implementation(
            http_client=http_client,
        )

    def create(
        self,
        name_or_configs: (
            str
            | dict[str, Any]
        ),
        config: Any | None = None,
    ):
        """
        Create one aggregator or all configured aggregators.

        Supported forms:

            create("1inch", config)

        or:

            create(config.aggregators)
        """

        if isinstance(
            name_or_configs,
            dict,
        ):
            return self.create_enabled(
                name_or_configs
            )

        if config is None:
            raise TypeError(
                "config is required when creating "
                "a single aggregator."
            )

        return self._create_one(
            name_or_configs,
            config,
        )

    def create_enabled(
        self,
        aggregators: dict[
            str,
            Any,
        ],
    ) -> AggregatorInstanceRegistry:
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

        result = AggregatorInstanceRegistry()

        for name, config in aggregators.items():
            if not self._registry_contains(name):
                raise AggregatorConfigurationError(
                    f"Unknown aggregator: '{name}'."
                )

            enabled = getattr(
                config,
                "enabled",
                None,
            )

            if enabled:
                instance = self._create_one(
                    name,
                    config,
                )

                result.register(
                    name,
                    instance,
                )

        if len(result) == 0:
            raise AggregatorConfigurationError(
                "No enabled aggregators were created."
            )

        return result
