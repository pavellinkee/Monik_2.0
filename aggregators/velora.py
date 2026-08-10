"""
Velora aggregator adapter.

Responsibility:
    Communicates with the Velora / ParaSwap API
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
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.http_client import HttpClient
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest


class VeloraAggregator(AggregatorInterface):
    """Velora API adapter."""

    BASE_URL = "https://api.paraswap.io"

    NAME = "Velora"

    OFFICIAL_URL = "https://velora.xyz"

    API_VERSION = "6.2"

    def __init__(
        self,
        http_client: HttpClient,
        api_key: str | None = None,
    ):
        self._http_client = http_client
        self._api_key = api_key

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
        request: QuoteRequest | None = None,
        **kwargs: Any,
    ) -> Quote:
        """
        Request and normalize a Velora quote.

        QuoteRequest is the primary interface.

        Legacy keyword arguments are supported for
        existing compatibility callers.
        """

        legacy_call = request is None

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
                token_in_decimals=kwargs.pop(
                    "token_in_decimals",
                    18,
                ),
                token_out_decimals=kwargs.pop(
                    "token_out_decimals",
                    18,
                ),
                requester_address=kwargs.pop(
                    "requester_address",
                    None,
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

        if request.token_in_decimals is None:
            raise AggregatorResponseError(
                "token decimals: "
                "token_in_decimals is required"
            )

        if request.token_out_decimals is None:
            raise AggregatorResponseError(
                "token decimals: "
                "token_out_decimals is required"
            )

        url = (
            f"{self.BASE_URL}/prices"
        )

        headers = {
            "Accept": "application/json",
        }

        if self._api_key:
            headers["X-API-KEY"] = (
                self._api_key
            )

        params = {
            "srcToken": request.token_in,
            "srcDecimals": (
                request.token_in_decimals
            ),
            "destToken": request.token_out,
            "destDecimals": (
                request.token_out_decimals
            ),
            "amount": str(
                request.amount
            ),
            "network": str(
                request.chain_id
            ),
            "side": "SELL",
            "version": self.API_VERSION,
        }

        if request.requester_address:
            params["userAddress"] = (
                request.requester_address
            )

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
                f"Velora request failed: {error}"
            ) from error

        if status == 429:
            raise AggregatorRateLimitError(
                "Velora rate limit reached."
            )

        if status >= 400:
            raise AggregatorRequestError(
                f"Velora returned HTTP {status}: "
                f"{data}"
            )

        if not isinstance(data, dict):
            raise AggregatorResponseError(
                "Velora returned a non-object "
                "response."
            )

        price_route = data.get(
            "priceRoute"
        )

        if not isinstance(
            price_route,
            dict,
        ):
            raise AggregatorResponseError(
                "Velora response does not contain "
                "a valid priceRoute."
            )

        amount_out = (
            self._extract_amount_out(
                price_route
            )
        )

        gas_estimate = (
            self._parse_optional_int(
                price_route.get(
                    "gasCost"
                )
            )
        )

        if gas_estimate is None:
            gas_estimate = (
                self._parse_optional_int(
                    price_route.get("gas")
                )
            )

        gas_cost_native = None

        price_impact = (
            self._parse_optional_decimal(
                price_route.get(
                    "priceImpact"
                )
            )
        )

        route = self._extract_route(
            price_route
        )

        timestamp = price_route.get(
            "blockNumber"
        )

        if timestamp is None:
            timestamp = price_route.get(
                "timestamp",
                data.get(
                    "timestamp",
                    "",
                ),
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
        """Check whether the HTTP client is available."""

        return self._http_client is not None

    @staticmethod
    def _extract_amount_out(
        price_route: dict[str, Any],
    ) -> int:
        """Extract destination token amount."""

        value = price_route.get(
            "destAmount"
        )

        if value is None:
            raise AggregatorResponseError(
                "Velora response does not contain "
                "destAmount."
            )

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise AggregatorResponseError(
                "Velora returned an invalid "
                "destAmount."
            ) from error

    @staticmethod
    def _parse_optional_int(
        value: Any,
    ) -> int | None:
        """Convert an optional value to int."""

        if value is None:
            return None

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
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

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _extract_route(
        price_route: dict[str, Any],
    ) -> str | None:
        """Extract a compact route description."""

        best_route = price_route.get(
            "bestRoute"
        )

        if isinstance(
            best_route,
            str,
        ):
            return best_route

        if not isinstance(
            best_route,
            list,
        ):
            return None

        names: list[str] = []

        def collect_names(
            value: Any,
        ) -> None:
            if isinstance(value, dict):
                exchange = value.get(
                    "exchange"
                )

                if exchange:
                    names.append(
                        str(exchange)
                    )

                pool = value.get(
                    "pool"
                )

                if pool:
                    names.append(
                        str(pool)
                    )

                for nested in value.values():
                    collect_names(nested)

            elif isinstance(value, list):
                for item in value:
                    collect_names(item)

        collect_names(best_route)

        if not names:
            return None

        unique_names = list(
            dict.fromkeys(names)
        )

        return " → ".join(
            unique_names
        )
