"""
1inch aggregator adapter.

Responsibility:
    Communicates with the 1inch Swap API quote endpoint
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
from aggregators.quote import Quote
from aggregators.http_client import HttpClient


class OneInchAggregator(AggregatorInterface):
    """1inch Swap API adapter."""

    BASE_URL = "https://api.1inch.dev/swap/v6.0"

    NAME = "1inch"

    OFFICIAL_URL = "https://1inch.com"

    def __init__(
        self,
        http_client: HttpClient,
        api_key: str,
    ):
        if not api_key:
            raise AggregatorConfigurationError(
                "1inch API key is required."
            )

        self._http_client = http_client
        self._api_key = api_key

    @property
    def name(self) -> str:
        """Return the aggregator name."""
        return self.NAME

    @property
    def official_url(self) -> str:
        """Return the official 1inch website."""
        return self.OFFICIAL_URL

    async def get_quote(
        self,
        chain_id: int,
        token_in: str,
        token_out: str,
        amount: int,
    ) -> Quote:
        """Request and normalize a 1inch quote."""

        if chain_id <= 0:
            raise ValueError("chain_id must be greater than 0")

        if not token_in:
            raise ValueError("token_in is required")

        if not token_out:
            raise ValueError("token_out is required")

        if amount <= 0:
            raise ValueError("amount must be greater than 0")

        url = (
            f"{self.BASE_URL}/{chain_id}/quote"
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        params = {
            "src": token_in,
            "dst": token_out,
            "amount": str(amount),
        }

        try:
            status, data = await self._http_client.get(
                url,
                headers=headers,
                params=params,
            )

        except Exception as error:
            raise AggregatorRequestError(
                f"1inch request failed: {error}"
            ) from error

        if status == 429:
            raise AggregatorRateLimitError(
                "1inch rate limit reached."
            )

        if status >= 400:
            raise AggregatorRequestError(
                f"1inch returned HTTP {status}: {data}"
            )

        if not isinstance(data, dict):
            raise AggregatorResponseError(
                "1inch returned a non-object response."
            )

        try:
            amount_out = int(data["dstAmount"])
        except (KeyError, TypeError, ValueError) as error:
            raise AggregatorResponseError(
                "1inch response does not contain a valid dstAmount."
            ) from error

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
            data.get("protocols")
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

        This does not send an additional request to 1inch.
        """
        return self._http_client is not None

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
        protocols: Any,
    ) -> str | None:
        """Convert 1inch protocol data into a compact route string."""
        if not protocols:
            return None

        if isinstance(protocols, str):
            return protocols

        if not isinstance(protocols, list):
            return str(protocols)

        parts: list[str] = []

        for item in protocols:
            if isinstance(item, list):
                for step in item:
                    if isinstance(step, list):
                        for part in step:
                            if isinstance(part, dict):
                                name = part.get(
                                    "name"
                                )

                                if name:
                                    parts.append(
                                        str(name)
                                    )

        if not parts:
            return str(protocols)

        return " → ".join(dict.fromkeys(parts))
