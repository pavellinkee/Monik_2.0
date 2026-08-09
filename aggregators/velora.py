"""
Velora aggregator adapter.

Responsibility:
    Communicates with the Velora Market API
    and converts the response into our common Quote model.

Does NOT:
    - implement rate limiting;
    - implement request queues;
    - implement failover;
    - calculate arbitrage;
    - send Telegram messages.

Authentication:
    The Market API endpoint used here does not require
    an API key.
"""

from decimal import Decimal
from typing import Any

from aggregators.aggregator_interface import AggregatorInterface
from aggregators.errors import (
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.http_client import HttpClient
from aggregators.quote import Quote


class VeloraAggregator(AggregatorInterface):
    """Velora Market API adapter."""

    BASE_URL = "https://api.paraswap.io"

    NAME = "Velora"

    OFFICIAL_URL = "https://velora.xyz"

    def __init__(
        self,
        http_client: HttpClient,
    ):
        self._http_client = http_client

    @property
    def name(self) -> str:
        """Return the aggregator name."""
        return self.NAME

    @property
    def official_url(self) -> str:
        """Return the official Velora website."""
        return self.OFFICIAL_URL

    async def get_quote(
        self,
        chain_id: int,
        token_in: str,
        token_out: str,
        amount: int,
    ) -> Quote:
        """Request and normalize a Velora market quote."""

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

        url = f"{self.BASE_URL}/prices"

        params = {
            "srcToken": token_in,
            "destToken": token_out,
            "amount": str(amount),
            "network": str(chain_id),
        }

        headers = {
            "Accept": "application/json",
        }

        try:
            status, data = await self._http_client.get(
                url,
                headers=headers,
                params=params,
            )

        except Exception as error:
            raise AggregatorRequestError(
                f"Velora request failed: {error}"
            ) from error

        if status == 429:
            raise AggregatorRateLimitError(
                "Velora rate limit reached."
            )

        if status >= 400:
            raise AggregatorRequestError(
                f"Velora returned HTTP {status}: {data}"
            )

        if not isinstance(data, dict):
            raise AggregatorResponseError(
                "Velora returned a non-object response."
            )

        price_route = data.get("priceRoute")

        if not isinstance(price_route, dict):
            raise AggregatorResponseError(
                "Velora response does not contain "
                "a valid priceRoute."
            )

        amount_out = self._extract_amount_out(
            price_route
        )

        gas_estimate = self._parse_optional_int(
            price_route.get("gasCost")
        )

        gas_cost_native = self._parse_optional_decimal(
            price_route.get("gasCost")
        )

        price_impact = self._parse_optional_decimal(
            price_route.get("priceImpact")
        )

        route = self._extract_route(
            price_route
        )

        timestamp = price_route.get(
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
        price_route: dict[str, Any],
    ) -> int:
        """Extract destination amount."""

        candidates = (
            price_route.get("destAmount"),
            price_route.get("destAmountAfterFee"),
        )

        for value in candidates:
            if value is None:
                continue

            try:
                return int(value)
            except (TypeError, ValueError):
                continue

        raise AggregatorResponseError(
            "Velora response does not contain "
            "a valid destination amount."
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
        price_route: dict[str, Any],
    ) -> str | None:
        """Extract a compact route description."""

        best_route = price_route.get(
            "bestRoute"
        )

        if best_route is None:
            return None

        if isinstance(best_route, str):
            return best_route

        return str(best_route)
