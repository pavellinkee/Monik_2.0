"""
HTTP client manager.

Responsibility:
    Creates, stores and manages shared HttpClient instances.

Rules:
    - One manager can own multiple named HTTP clients.
    - Clients can be created lazily.
    - Existing clients are reused.
    - Only enabled aggregators receive HTTP clients.
    - All clients can be started and stopped centrally.
    - HTTP transport settings are kept separate from
      aggregator-specific API credentials.
    - Aggregator-specific rate limits are handled elsewhere.

Does NOT:
    - make scanner decisions;
    - apply aggregator-specific rate limits;
    - manage request priority;
    - interpret aggregator responses;
    - know about Stage 1 or Stage 2;
    - store or transmit API keys.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aggregators.http_client import HttpClient


class HttpClientManager:
    """
    Manages reusable HttpClient instances.

    The manager provides a single lifecycle owner for HTTP
    sessions used by aggregator adapters.
    """

    def __init__(
        self,
        default_timeout_seconds: float = 10.0,
        default_connector_limit: int = 100,
    ):
        if default_timeout_seconds <= 0:
            raise ValueError(
                "default_timeout_seconds must be "
                "greater than 0"
            )

        if default_connector_limit <= 0:
            raise ValueError(
                "default_connector_limit must be "
                "greater than 0"
            )

        self._default_timeout_seconds = (
            default_timeout_seconds
        )

        self._default_connector_limit = (
            default_connector_limit
        )

        self._clients: dict[
            str,
            HttpClient,
        ] = {}

    @property
    def default_timeout_seconds(self) -> float:
        """Return the default HTTP timeout."""

        return self._default_timeout_seconds

    @property
    def default_connector_limit(self) -> int:
        """Return the default connection limit."""

        return self._default_connector_limit

    def add(
        self,
        name: str,
        client: HttpClient,
    ) -> None:
        """
        Register an existing HTTP client.
        """

        self._validate_name(name)

        if not isinstance(
            client,
            HttpClient,
        ):
            raise TypeError(
                "client must be an HttpClient"
            )

        if name in self._clients:
            raise ValueError(
                f"HTTP client '{name}' already exists."
            )

        self._clients[name] = client

    def create(
        self,
        name: str,
        *,
        timeout_seconds: float | None = None,
        connector_limit: int | None = None,
    ) -> HttpClient:
        """
        Create and register a new HTTP client.

        If a client with the same name already exists,
        ValueError is raised.
        """

        self._validate_name(name)

        if name in self._clients:
            raise ValueError(
                f"HTTP client '{name}' already exists."
            )

        client = HttpClient(
            timeout_seconds=(
                self._default_timeout_seconds
                if timeout_seconds is None
                else timeout_seconds
            ),
            connector_limit=(
                self._default_connector_limit
                if connector_limit is None
                else connector_limit
            ),
        )

        self._clients[name] = client

        return client

    def create_for_aggregators(
        self,
        aggregators: Mapping[str, Any],
    ) -> None:
        """
        Create one HTTP client for every enabled aggregator.

        The method accepts the aggregator configuration mapping
        from ScannerConfig.

        Only the following configuration property is required:

            enabled

        API keys and rate-limit settings are intentionally ignored.
        They belong to higher-level aggregator components.
        """

        if not isinstance(
            aggregators,
            Mapping,
        ):
            raise TypeError(
                "aggregators must be a mapping."
            )

        for name, config in aggregators.items():
            self._validate_name(name)

            enabled = getattr(
                config,
                "enabled",
                None,
            )

            if enabled is None:
                raise ValueError(
                    f"Aggregator '{name}' configuration "
                    f"does not provide 'enabled'."
                )

            if not enabled:
                continue

            if self.contains(name):
                continue

            self.create(name)

    def get(
        self,
        name: str,
    ) -> HttpClient:
        """
        Return a registered HTTP client.
        """

        try:
            return self._clients[name]

        except KeyError:
            raise KeyError(
                f"Unknown HTTP client: '{name}'."
            ) from None

    def get_or_create(
        self,
        name: str,
        *,
        timeout_seconds: float | None = None,
        connector_limit: int | None = None,
    ) -> HttpClient:
        """
        Return an existing client or create a new one.
        """

        if name in self._clients:
            return self._clients[name]

        return self.create(
            name,
            timeout_seconds=timeout_seconds,
            connector_limit=connector_limit,
        )

    def contains(
        self,
        name: str,
    ) -> bool:
        """Return whether a client is registered."""

        return name in self._clients

    def names(self) -> tuple[str, ...]:
        """Return registered client names."""

        return tuple(
            self._clients.keys()
        )

    def all(self) -> tuple[HttpClient, ...]:
        """Return all registered HTTP clients."""

        return tuple(
            self._clients.values()
        )

    def remove(
        self,
        name: str,
    ) -> HttpClient:
        """
        Remove and return a client.

        The client is not closed automatically.
        Lifecycle management remains explicit.
        """

        try:
            return self._clients.pop(name)

        except KeyError:
            raise KeyError(
                f"Unknown HTTP client: '{name}'."
            ) from None

    async def start_all(self) -> None:
        """Start all registered HTTP clients."""

        for client in self._clients.values():
            await client.start()

    async def close_all(self) -> None:
        """Close all registered HTTP clients."""

        for client in self._clients.values():
            await client.close()

    async def __aenter__(
        self,
    ) -> "HttpClientManager":
        """Start all clients for async context usage."""

        await self.start_all()

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """Close all clients after async context usage."""

        await self.close_all()

    @staticmethod
    def _validate_name(
        name: str,
    ) -> None:
        """Validate a client name."""

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "client name must be a string"
            )

        if not name.strip():
            raise ValueError(
                "client name cannot be empty"
            )
