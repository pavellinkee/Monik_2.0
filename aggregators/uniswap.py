"""
Uniswap Trading API aggregator adapter.

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
from aggregators.quote_request import QuoteRequest


class UniswapAggregator(AggregatorInterface):
    """Uniswap Trading API adapter."""

    BASE_URL = (
        "https://trade-api.gateway.uniswap.org"
        "/v1/quote"
    )

    NAME = "Uniswap"

    OFFICIAL_URL = "https://uniswap.org"

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
        request: QuoteRequest,
    ) -> Quote:
        """Request and normalize a Uniswap quote."""

        if not request.requester_address:
            raise AggregatorConfigurationError(
                "Uniswap quote requires requester_address."
            )

        headers = {
            "x-api-key": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-universal-router-version": "2.0",
        }

        payload = {
            "type": "EXACT_INPUT",
            "amount": str(request.amount),
            "tokenInChainId": request.chain_id,
            "tokenOutChainId": request.chain_id,
            "tokenIn": request.token_in,
            "tokenOut": request.token_out,
            "swapper": request.requester_address,
        }

        try:
            status, data = await self._http_client.post(
                self.BASE_URL,
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

        quote_data = data.get("quote")

        if not isinstance(
            quote_data,
            dict,
        ):
            raise AggregatorResponseError(
                "Uniswap response does not contain "
                "a valid quote object."
            )

        amount_out = self._extract_amount_out(
            quote_data
        )

        gas_estimate = self._extract_gas_estimate(
            data
        )

        gas_cost_native = self._extract_gas_cost(
            data
        )

        routing = data.get(
            "routing"
        )

        route = (
            str(routing)
            if routing
            else None
        )

        request_id = data.get(
            "requestId",
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
            timestamp=str(request_id),
        )

    async def is_available(self) -> bool:
        """
        Check whether the HTTP client is available.

        This does not send an additional request.
        """

        return self._http_client is not None

    @staticmethod
    def _extract_amount_out(
        quote_data: dict[str, Any],
    ) -> int:
        """Extract output amount from a Uniswap quote."""

        output = quote_data.get("output")

        if isinstance(output, dict):
            value = output.get("amount")

            if value is not None:
                try:
                    return int(value)

                except (TypeError, ValueError) as error:
                    raise AggregatorResponseError(
                        "Uniswap returned an invalid "
                        "output amount."
                    ) from error

        order_info = quote_data.get(
            "orderInfo"
        )

        if isinstance(
            order_info,
            dict,
        ):
            outputs = order_info.get(
                "outputs"
            )

            if isinstance(
                outputs,
                list,
            ) and outputs:

                first_output = outputs[0]

                if isinstance(
                    first_output,
                    dict,
                ):
                    value = first_output.get(
                        "startAmount"
                    )

                    if value is not None:
                        try:
                            return int(value)

                        except (
                            TypeError,
                            ValueError,
                        ) as error:
                            raise AggregatorResponseError(
                                "Uniswap returned an invalid "
                                "order output amount."
                            ) from error

        raise AggregatorResponseError(
            "Uniswap response does not contain "
            "an output amount."
        )

    @staticmethod
    def _extract_gas_estimate(
        data: dict[str, Any],
    ) -> int | None:
        """Extract estimated gas units."""

        permit_transaction = data.get(
            "permitTransaction"
        )

        if not isinstance(
            permit_transaction,
            dict,
        ):
            return None

        value = permit_transaction.get(
            "gasLimit"
        )

        if value is None:
            return None

        try:
            return int(value)

        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_gas_cost(
        data: dict[str, Any],
    ) -> Decimal | None:
        """
        Extract total estimated gas cost.

        Uniswap provides this value in the chain's base unit.
        """

        value = data.get(
            "permitGasFee"
        )

        if value is None:
            return None

        try:
            return Decimal(str(value)) / Decimal(
                10 ** 18
            )

        except (TypeError, ValueError) as error:
            raise AggregatorResponseError(
                "Uniswap returned an invalid "
                "permitGasFee."
            ) from error
