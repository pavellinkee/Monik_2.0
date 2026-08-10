"""
Common asynchronous HTTP client.

Responsibility:
    Provides a shared HTTP interface for aggregator adapters.

Features:
    - asynchronous GET and POST requests;
    - reusable aiohttp session;
    - configurable timeout;
    - configurable connection limit;
    - automatic session creation;
    - safe session shutdown;
    - HTTP status preservation;
    - JSON response decoding;
    - text fallback for non-JSON responses;
    - normalized request errors.

Does NOT:
    - apply aggregator-specific rate limits;
    - implement failover;
    - know about Stage 1 or Stage 2;
    - interpret aggregator responses;
    - calculate opportunities;
    - manage request priority.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class HttpClientError(Exception):
    """Base exception for HTTP client errors."""


class HttpRequestError(HttpClientError):
    """Raised when an HTTP request cannot be completed."""


class HttpClient:
    """Shared asynchronous HTTP client."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        connector_limit: int = 100,
    ):
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than 0"
            )

        if connector_limit <= 0:
            raise ValueError(
                "connector_limit must be greater than 0"
            )

        self._timeout_seconds = timeout_seconds

        self._timeout = aiohttp.ClientTimeout(
            total=timeout_seconds
        )

        self._connector_limit = connector_limit

        self._session: (
            aiohttp.ClientSession | None
        ) = None

    @property
    def timeout_seconds(self) -> float:
        """Return configured request timeout."""

        return self._timeout_seconds

    @property
    def connector_limit(self) -> int:
        """Return configured connection limit."""

        return self._connector_limit

    @property
    def is_open(self) -> bool:
        """Return whether the HTTP session is open."""

        return (
            self._session is not None
            and not self._session.closed
        )

    async def start(self) -> None:
        """Create the HTTP session."""

        if self.is_open:
            return

        connector = aiohttp.TCPConnector(
            limit=self._connector_limit
        )

        self._session = aiohttp.ClientSession(
            timeout=self._timeout,
            connector=connector,
        )

    async def close(self) -> None:
        """Close the HTTP session."""

        if self._session is None:
            return

        if not self._session.closed:
            await self._session.close()

        self._session = None

    async def __aenter__(
        self,
    ) -> "HttpClient":
        """Start the client for async context usage."""

        await self.start()

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """Close the client after async context usage."""

        await self.close()

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        """
        Perform an HTTP GET request.

        Returns:
            Tuple containing HTTP status code and decoded
            response data.
        """

        return await self._request(
            method="GET",
            url=url,
            headers=headers,
            params=params,
        )

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        """
        Perform an HTTP POST request.

        Returns:
            Tuple containing HTTP status code and decoded
            response data.
        """

        return await self._request(
            method="POST",
            url=url,
            headers=headers,
            params=params,
            json=json,
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> tuple[int, Any]:
        """Perform a normalized HTTP request."""

        if not isinstance(
            url,
            str,
        ) or not url.strip():
            raise ValueError(
                "url must be a non-empty string"
            )

        await self.start()

        assert self._session is not None

        try:
            async with self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
            ) as response:

                status = response.status

                data = await self._read_response(
                    response
                )

                return status, data

        except asyncio.TimeoutError as error:
            raise HttpRequestError(
                f"HTTP request timed out: "
                f"{method} {url}"
            ) from error

        except aiohttp.ClientError as error:
            raise HttpRequestError(
                f"HTTP request failed: "
                f"{method} {url}"
            ) from error

    @staticmethod
    async def _read_response(
        response: aiohttp.ClientResponse,
    ) -> Any:
        """
        Decode an HTTP response.

        JSON responses are decoded as JSON.
        Non-JSON responses are returned as text.
        Empty responses return None.
        """

        if response.status == 204:
            return None

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            ).lower()
        )

        if "json" in content_type:
            return await response.json(
                content_type=None
            )

        text = await response.text()

        if not text:
            return None

        return text
