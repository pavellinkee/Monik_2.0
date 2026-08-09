"""
Common asynchronous HTTP client.

Responsibility:
    Provides a shared HTTP interface for aggregator adapters.

Does NOT:
    - apply aggregator-specific rate limits;
    - implement failover;
    - know about Stage 1 or Stage 2;
    - interpret aggregator responses.
"""

from typing import Any

import aiohttp


class HttpClient:
    """Shared asynchronous HTTP client."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
    ):
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than 0"
            )

        self._timeout = aiohttp.ClientTimeout(
            total=timeout_seconds
        )

        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """Create the HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            await self._session.close()
            self._session = None

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
            Tuple containing HTTP status code and decoded JSON.
        """
        if self._session is None:
            raise RuntimeError(
                "HttpClient must be started before use."
            )

        async with self._session.get(
            url,
            headers=headers,
            params=params,
        ) as response:
            status = response.status
            data = await response.json(
                content_type=None
            )

            return status, data

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
            Tuple containing HTTP status code and decoded JSON.
        """
        if self._session is None:
            raise RuntimeError(
                "HttpClient must be started before use."
            )

        async with self._session.post(
            url,
            headers=headers,
            json=json,
            params=params,
        ) as response:
            status = response.status
            data = await response.json(
                content_type=None
            )

            return status, data
