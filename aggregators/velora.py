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


class VeloraAggregator(AggregatorInterface):
    """Velora API adapter."""

    BASE_URL = "https://api.paraswap.io"

    NAME = "Velora"

    OFFICIAL_URL = "https://velora.xyz"

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
        chain_id: int,
        token_in: str,
        token_out: str,
        amount: int,
    ) -> Quote:
        """
        Request and normalize a Velora quote.

        The adapter uses the common aggregator interface:
            chain_id
            token_in
            token_out
            amount
        """

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
            "srcToken": token_in,
            "destToken": token_out,
            "amount": str(amount),
            "network": str(chain_id),
            "side": "SELL",
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
                f"Velora request failed: {error}"
            ) from error

        if status == 429:
            raise AggregatorRateLimitError(
                "Velora rate limit reached."
            )

        if status >= 400:
            raise AggregatorRequestError(
                f"Velora returned HTTP "
                f"{status}: {data}"
            )

        if not isinstance(
            data,
            dict,
        ):
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
                price_route.get("gas")
            )
