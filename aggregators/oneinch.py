"""
1inch aggregator adapter.

Responsibility:
    Communicates with the 1inch Swap API
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

from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.errors import (
    AggregatorConfigurationError,
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.http_client import HttpClient
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest


class OneInchAggregator(AggregatorInterface):
    """1inch Swap API adapter."""

    BASE_URL = (
        "https://api.1inch.dev/swap/v6.1"
    )

    NAME = "1inch"

    OFFICIAL_URL = "https://1inch.com"

    NATIVE_TOKEN_DECIMALS = 18

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
        request: QuoteRequest | None = None,
        **kwargs: Any,
    ) -> Quote:
        """
        Request and normalize a 1inch quote.

        The current API accepts QuoteRequest.

        Legacy keyword arguments are supported for compatibility
        with the existing aggregator tests and callers.
        """

        if request is None:
            request = QuoteRequest(
                chain_id=kwargs.pop(
                    "chain_id"
                ),
                token_in=kwargs.pop(
                    "token_in"
                ),
                token_out=kwargs.pop(
                    "token_out"
                ),
                amount=kwargs.pop(
                    "amount"
                ),
            )

        if kwargs:
            unexpected = ", ".join(
                sorted(kwargs.keys())
            )

            raise TypeError(
                "Unexpected get_quote arguments: "
                f"{unexpected}"
            )

        url = (
            f"{self.BASE_URL}"
            f"/{request.chain_id}/quote"
        )

        headers = {
            "Authorization": (
                f"Bearer {self._api_key}"
            ),
            "Accept": "application/json",
        }

        params = {
            "src": request.token_in,
            "dst": request.token_out,
            "amount": str(request.amount),
        }

        try:
            status, data = (
                await self._http_client.get(
                    url,
                    headers=headers,
                    params=params,
                )
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

        amount_out = self._extract_amount_out(
            data
        )

        gas_estimate = self._parse_optional_int(
            data.get("gas")
        )

        gas_cost_native = self._parse_gas_cost(
            data.get("gasCost")
        )

        price_impact = (
            self._parse_optional_decimal(
                data.get("priceImpact")
            )
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
            chain_id=request.chain_id,
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount,
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

        This does not send an additional request.
        """

        return self._http_client is not None

    @staticmethod
    def _extract_amount_out(
        data: dict[str, Any],
    ) -> int:
        """Extract destination token amount."""

        value = data.get(
            "dstAmount"
        )

        if value is None:
            raise AggregatorResponseError(
                "1inch response does not contain "
                "dstAmount."
            )

        try:
            return int(value)

        except (TypeError, ValueError) as error:
            raise AggregatorResponseError(
                "1inch returned an invalid dstAmount."
            ) from error

    @classmethod
    def _parse_gas_cost(
        cls,
        value: Any,
    ) -> Decimal | None:
        """
        Convert gas cost from wei to native token units.

        1inch returns gasCost in the smallest
        native-token denomination.
        """

        if value is None:
            return None

        try:
            gas_cost_wei = Decimal(
                str(value)
            )

        except (TypeError, ValueError) as error:
            raise AggregatorResponseError(
                "1inch returned an invalid gasCost."
            ) from error

        divisor = Decimal(
            10 ** cls.NATIVE_TOKEN_DECIMALS
        )

        return gas_cost_wei / divisor

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
            return Decimal(
                str(value)
            )

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_route(
        data: dict[str, Any],
    ) -> str | None:
        """Extract a compact route description."""

        protocols = data.get(
            "protocols"
        )

        if protocols is None:
            return None

        if not isinstance(
            protocols,
            list,
        ):
            return str(protocols)

        names: list[str] = []

        def collect_names(
            value: Any,
        ) -> None:
            if isinstance(value, dict):
                name = value.get(
                    "name"
                )

                if name:
                    names.append(
                        str(name)
                    )

                for nested in value.values():
                    collect_names(nested)

            elif isinstance(value, list):
                for item in value:
                    collect_names(item)

        collect_names(protocols)

        if not names:
            return None

        unique_names = list(
            dict.fromkeys(names)
        )

        return " → ".join(
            unique_names
        )
