"""
Velora Market API v6.2 aggregator adapter.

Responsibility:
    Communicates with the Velora Market API
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
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.http_client import HttpClient
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest


class VeloraAggregator(AggregatorInterface):
    """Velora Market API v6.2 adapter."""

    BASE_URL = (
        "https://api.paraswap.io/prices"
    )

    NAME = "Velora"

    OFFICIAL_URL = "https://velora.xyz"

    API_VERSION = "6.2"

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
        request: QuoteRequest,
    ) -> Quote:
        """Request and normalize a Velora quote."""

        if (
            request.token_in_decimals is None
            or request.token_out_decimals is None
        ):
            raise AggregatorResponseError(
                "Velora quote requires token decimals."
            )

        params = {
            "srcToken": request.token_in,
            "srcDecimals": str(
                request.token_in_decimals
            ),
            "destToken": request.token_out,
            "destDecimals": str(
                request.token_out_decimals
            ),
            "amount": str(request.amount),
            "side": "SELL",
            "network": str(request.chain_id),
            "version": self.API_VERSION,
        }

        if request.requester_address:
            params["userAddress"] = (
                request.requester_address
            )

        try:
            status, data = await self._http_client.get(
                self.BASE_URL,
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

        amount_out = self._extract_amount_out(
            price_route
        )

        gas_estimate = self._parse_optional_int(
            price_route.get("gasCost")
        )

        route = self._extract_route(
            price_route
        )

        block_number = price_route.get(
            "blockNumber",
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
            gas_cost_native=None,
            price_impact=None,
            route=route,
            timestamp=str(block_number),
        )

    async def is_available(self) -> bool:
        """
        Check whether the HTTP client is available.

        This does not send an additional request.
        """

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

        except (TypeError, ValueError) as error:
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

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_route(
        price_route: dict[str, Any],
    ) -> str | None:
        """Extract exchange names from bestRoute."""

        best_route = price_route.get(
            "bestRoute"
        )

        if not isinstance(
            best_route,
            list,
        ):
            return None

        exchanges: list[str] = []

        for route_part in best_route:
            if not isinstance(
                route_part,
                dict,
            ):
                continue

            swaps = route_part.get(
                "swaps"
            )

            if not isinstance(
                swaps,
                list,
            ):
                continue

            for swap in swaps:
                if not isinstance(
                    swap,
                    dict,
                ):
                    continue

                swap_exchanges = swap.get(
                    "swapExchanges"
                )

                if isinstance(
                    swap_exchanges,
                    list,
                ):
                    for exchange in swap_exchanges:
                        if not isinstance(
                            exchange,
                            dict,
                        ):
                            continue

                        name = exchange.get(
                            "exchange"
                        )

                        if name:
                            exchanges.append(
                                str(name)
                            )

                exchange = swap.get(
                    "exchange"
                )

                if exchange:
                    exchanges.append(
                        str(exchange)
                    )

        if not exchanges:
            return None

        return " → ".join(
            dict.fromkeys(exchanges)
        )
