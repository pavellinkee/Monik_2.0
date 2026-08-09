"""
0x aggregator adapter.

Responsibility:
    Communicates with the 0x Swap API price endpoint
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


class ZeroXAggregator(AggregatorInterface):
    """0x Swap API adapter."""

    BASE_URL = "https://api.0x.org"

    NAME = "0x"

    OFFICIAL_URL = "https://0x.org"

    def __init__(
        self,
        http_client: HttpClient,
        api_key: str,
    ):
        if not api_key:
            raise AggregatorConfigurationError(
                "0x API key is required."
            )

        self._http_client = http_client
        self._api_key = api_key

    @property
    def name(self) -> str:
        """Return the aggregator name."""
        return self.NAME

    @property
    def official_url(self) -> str:
        """Return the official 0x website."""
        return self.OFFICIAL_URL

    async def get_quote(
        self,
        chain_id: int,
        token_in: str,
        token_out: str,
        amount: int,
    ) -> Quote:
        """Request and normalize a 0x price quote."""

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

        url = (
            f"{self.BASE_URL}"
            "/swap/allowance-holder/price"
        )

        headers = {
            "0x-api-key": self._api_key,
            "0x-version": "v2",
            "Accept": "application/json",
        }

        params = {
            "chainId": str(chain_id),
            "sellToken": token_in,
            "buyToken": token_out,
            "sellAmount": str(amount),
        }

        try:
            status, data = await self._http_client.get(
                url,
                headers=headers,
                params=params,
            )

        except Exception as error:
            raise AggregatorRequestError(
                f"0x request failed: {error}"
            ) from error

        if status == 429:
            raise AggregatorRateLimitError(
                "0x rate limit reached."
            )

        if status >= 400:
            raise AggregatorRequestError(
                f"0x returned HTTP {status}: {data}"
            )

        if not isinstance(data, dict):
            raise AggregatorResponseError(
                "0x returned a non-object response."
            )

        amount_out = self._extract_amount_out(
            data
        )

        gas_estimate = self._parse_optional_int(
            data.get("gas")
        )

        gas_cost_native = self._parse_optional_decimal(
            data.get("gasCost")
        )

        price_impact = self._parse_optional_decimal(
            data.get("priceImpact")
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

        This does not send an additional request to 0x.
        """
        return self._http_client is not None

    @staticmethod
    def _extract_amount_out(
        data: dict[str, Any],
    ) -> int:
        """Extract the buy amount from a 0x response."""

        candidates = (
            data.get("buyAmount"),
            data.get("buyAmount"),
            data.get("buyTokenAmount"),
        )

        for value in candidates:
            if value is None:
                continue

            try:
                return int(value)
            except (TypeError, ValueError):
                continue

        raise AggregatorResponseError(
            "0x response does not contain a valid "
            "output token amount."
        )

    @staticmethod
    def _parse_optional_int(
        value: Any,
    ) -> int | None:
        """Convert an optional value to int."""

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_optional_decimal(
        value: Any,
    ) -> Decimal | None:
        """Convert an optional value to Decimal."""

        if value is None:
            return None

        try:
            return Decimal(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_route(
        data: dict[str, Any],
    ) -> str | None:
        """Extract a compact route description."""

        route = data.get("route")

        if route is None:
            return None

        if isinstance(route, str):
            return route

        return str(route)
