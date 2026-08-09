"""
Uniswap aggregator adapter.

Responsibility:
    Communicates with the Uniswap Trading API
    and converts the response into our common Quote model.

Does NOT:
    - implement rate limiting;
    - implement request queues;
    - implement failover;
    - calculate arbitrage;
    - send Telegram messages.
"""

from decimal import Decimal
from typing import Any

from aggregators.aggregator_interface import AggregatorInterface
from aggregators.errors import (
    AggregatorConfigurationError,
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.http_client import HttpClient
from aggregators.quote import Quote


class UniswapAggregator(AggregatorInterface):
    """Uniswap Trading API adapter."""

    BASE_URL = "https://trade-api.gateway.uniswap.org/v1"

    NAME = "Uniswap"

    OFFICIAL_URL = "https://app.uniswap.org"

    def __init__(
        self,
        http_client: HttpClient,
        api_key: str,
    ):
        if not api_key:
            raise AggregatorConfigurationError(
                "Uniswap API key is required."
            )

        self._http_client = http_client
        self._api_key = api_key

    @property
    def name(self) -> str:
        """Return the aggregator name."""
        return self.NAME

    @property
    def official_url(self) -> str:
        """Return the official Uniswap website."""
        return self.OFFICIAL_URL

    async def get_quote(
        self,
        chain_id: int,
        token_in: str,
        token_out: str,
        amount: int,
    ) -> Quote:
        """Request and normalize a Uniswap quote."""

        if chain_id <= 0:
            raise ValueError(
                "chain_id must be greater than 0"
            )

        if not token_in:
            raise ValueError(
                "token_in is required"
            )

        if not token_out:
            raise ValueError(
                "token_out is required"
            )

        if amount <= 0:
            raise ValueError(
                "amount must be greater than 0"
            )

        url = f"{self.BASE_URL}/quote"

        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "type": "EXACT_INPUT",
            "amount": str(amount),
            "tokenIn": token_in,
            "tokenOut": token_out,
            "chainId": chain_id,
        }

        try:
            status, data = await self._http_client.post(
                url,
                headers=headers,
                json=payload,
            )

        except Exception as error:
            raise AggregatorRequestError(
                f"Uniswap request failed: {error}"
            ) from error

        if status == 429:
            raise AggregatorRateLimitError(
                "Uniswap rate limit reached."
            )

        if status >= 400:
            raise AggregatorRequestError(
                f"Uniswap returned HTTP {status}: {data}"
            )

        if not isinstance(data, dict):
            raise AggregatorResponseError(
                "Uniswap returned a non-object response."
            )

        amount_out = self._extract_amount_out(
            data
        )

        gas_estimate = self._extract_gas_estimate(
            data
        )

        gas_cost_native = self._extract_gas_cost(
            data
        )

        price_impact = self._extract_price_impact(
            data
        )

        route = self._extract_route(
            data
        )

        timestamp = data.get(
            "timestamp",
            "",
        )

        return Quote(
            aggregator=self.name,
            chain_id=chain_id,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount,
            amount_out=amount_out,
            gas_estimate=gas_estimate,
            gas_cost_native=gas_cost_native,
            price_impact=price_impact,
            route=route,
            timestamp=str(timestamp),
        )

    async def is_available(self) -> bool:
        """
        Check whether the HTTP client is available.

        This does not send an additional API request.
        """
        return self._http_client is not None

    @staticmethod
    def _extract_amount_out(
        data: dict[str, Any],
    ) -> int:
        """Extract output token amount from the response."""

        candidates = (
            data.get("amountOut"),
            data.get("outputAmount"),
            data.get("quote", {}).get("amountOut")
            if isinstance(data.get("quote"), dict)
            else None,
        )

        for value in candidates:
            if value is None:
                continue

            try:
                return int(value)
            except (TypeError, ValueError):
                continue

        raise AggregatorResponseError(
            "Uniswap response does not contain a valid "
            "output token amount."
        )

    @staticmethod
    def _extract_gas_estimate(
        data: dict[str, Any],
    ) -> int | None:
        """Extract estimated gas usage."""

        candidates = (
            data.get("gasEstimate"),
            data.get("gas"),
            data.get("quote", {}).get("gasEstimate")
            if isinstance(data.get("quote"), dict)
            else None,
        )

        for value in candidates:
            if value is None:
                continue

            try:
                return int(value)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _extract_gas_cost(
        data: dict[str, Any],
    ) -> Decimal | None:
        """Extract estimated gas cost."""

        candidates = (
            data.get("gasCost"),
            data.get("gasCostNative"),
            data.get("quote", {}).get("gasCost")
            if isinstance(data.get("quote"), dict)
            else None,
        )

        for value in candidates:
            if value is None:
                continue

            try:
                return Decimal(str(value))
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _extract_price_impact(
        data: dict[str, Any],
    ) -> Decimal | None:
        """Extract price impact."""

        candidates = (
            data.get("priceImpact"),
            data.get("quote", {}).get("priceImpact")
            if isinstance(data.get("quote"), dict)
            else None,
        )

        for value in candidates:
            if value is None:
                continue

            try:
                return Decimal(str(value))
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _extract_route(
        data: dict[str, Any],
    ) -> str | None:
        """Extract a compact route description."""

        route = data.get("route")

        if route is None:
            route = data.get("routing")

        if route is None:
            return None

        if isinstance(route, str):
            return route

        return str(route)
