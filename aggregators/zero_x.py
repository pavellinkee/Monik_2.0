"""
0x Swap API v2 aggregator adapter.

Responsibility:
    Communicates with the 0x Swap API v2
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
from aggregators.quote_request import QuoteRequest


class ZeroXAggregator(AggregatorInterface):
    """0x Swap API v2 adapter."""

    BASE_URL = (
        "https://api.0x.org/"
        "swap/allowance-holder/quote"
    )

    NAME = "0x"

    OFFICIAL_URL = "https://0x.org"

    NATIVE_TOKEN_DECIMALS = 18

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
        request: QuoteRequest,
    ) -> Quote:
        """Request and normalize a 0x quote."""

        if not request.requester_address:
            raise AggregatorConfigurationError(
                "0x quote requires requester_address."
            )

        headers = {
            "0x-api-key": self._api_key,
            "0x-version": "v2",
            "Accept": "application/json",
        }

        params = {
            "chainId": str(request.chain_id),
            "buyToken": request.token_out,
            "sellToken": request.token_in,
            "sellAmount": str(request.amount),
            "taker": request.requester_address,
        }

        try:
            status, data = await self._http_client.get(
                self.BASE_URL,
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

        liquidity_available = data.get(
            "liquidityAvailable"
        )

        if liquidity_available is False:
            raise AggregatorResponseError(
                "0x reported no available liquidity."
            )

        amount_out = self._extract_amount_out(
            data
        )

        transaction = data.get(
            "transaction"
        )

        gas_estimate = self._extract_gas_estimate(
            transaction
        )

        gas_cost_native = (
            self._extract_network_fee(data)
        )

        route = self._extract_route(data)

        block_number = data.get(
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
            gas_cost_native=gas_cost_native,
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
        data: dict[str, Any],
    ) -> int:
        """Extract destination token amount."""

        value = data.get("buyAmount")

        if value is None:
            raise AggregatorResponseError(
                "0x response does not contain buyAmount."
            )

        try:
            return int(value)

        except (TypeError, ValueError) as error:
            raise AggregatorResponseError(
                "0x returned an invalid buyAmount."
            ) from error

    @staticmethod
    def _extract_gas_estimate(
        transaction: Any,
    ) -> int | None:
        """Extract estimated gas units."""

        if not isinstance(
            transaction,
            dict,
        ):
            return None

        value = transaction.get("gas")

        if value is None:
            return None

        try:
            return int(value)

        except (TypeError, ValueError):
            return None

    @classmethod
    def _extract_network_fee(
        cls,
        data: dict[str, Any],
    ) -> Decimal | None:
        """
        Convert totalNetworkFee from wei to native units.
        """

        value = data.get(
            "totalNetworkFee"
        )

        if value is None:
            return None

        try:
            fee_wei = Decimal(str(value))

        except (TypeError, ValueError) as error:
            raise AggregatorResponseError(
                "0x returned an invalid totalNetworkFee."
            ) from error

        return fee_wei / Decimal(
            10 ** cls.NATIVE_TOKEN_DECIMALS
        )

    @staticmethod
    def _extract_route(
        data: dict[str, Any],
    ) -> str | None:
        """Extract route sources from the response."""

        route = data.get("route")

        if not isinstance(route, dict):
            return None

        fills = route.get("fills")

        if not isinstance(fills, list):
            return None

        names: list[str] = []

        for fill in fills:
            if not isinstance(fill, dict):
                continue

            source = fill.get("source")

            if source:
                names.append(str(source))

        if not names:
            return None

        return " → ".join(
            dict.fromkeys(names)
        )
