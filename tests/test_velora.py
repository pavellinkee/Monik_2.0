"""
Tests for the Velora Market API v6.2 adapter.

These tests do not make real requests to the Velora API.
"""

import pytest

from aggregators.errors import (
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest
from aggregators.velora import VeloraAggregator


class FakeHttpClient:
    """Fake HTTP client used for unit tests."""

    def __init__(
        self,
        status: int,
        data,
    ):
        self.status = status
        self.data = data

    async def get(
        self,
        url: str,
        *,
        headers=None,
        params=None,
    ):
        """Return the predefined fake response."""

        return self.status, self.data


def make_request(
    with_decimals: bool = True,
) -> QuoteRequest:
    """Create a standard Velora test request."""

    return QuoteRequest(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000000,
        token_in_decimals=(
            6
            if with_decimals
            else None
        ),
        token_out_decimals=(
            18
            if with_decimals
            else None
        ),
    )


@pytest.mark.asyncio
async def test_get_quote_returns_normalized_quote():
    """Velora response is converted into Quote."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "priceRoute": {
                "destAmount": "1234567",
                "gasCost": "185000",
                "blockNumber": 12345678,
                "bestRoute": [
                    {
                        "swaps": [
                            {
                                "swapExchanges": [
                                    {
                                        "exchange": "UniswapV3",
                                    },
                                    {
                                        "exchange": "Curve",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
        },
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    quote = await aggregator.get_quote(
        make_request()
    )

    assert isinstance(quote, Quote)

    assert quote.aggregator == "Velora"
    assert quote.chain_id == 137

    assert quote.token_in == "0xTokenIn"
    assert quote.token_out == "0xTokenOut"

    assert quote.amount_in == 1000000000
    assert quote.amount_out == 1234567

    assert quote.gas_estimate == 185000
    assert quote.gas_cost_native is None

    assert quote.price_impact is None
    assert quote.route == "UniswapV3 → Curve"
    assert quote.timestamp == "12345678"


@pytest.mark.asyncio
async def test_get_quote_requires_token_decimals():
    """Velora requires both token decimal values."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    with pytest.raises(
        AggregatorResponseError,
        match="token decimals",
    ):
        await aggregator.get_quote(
            make_request(
                with_decimals=False
            )
        )


@pytest.mark.asyncio
async def test_get_quote_raises_rate_limit_error():
    """HTTP 429 becomes AggregatorRateLimitError."""

    http_client = FakeHttpClient(
        status=429,
        data={
            "error": "Too Many Requests",
        },
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    with pytest.raises(
        AggregatorRateLimitError
    ):
        await aggregator.get_quote(
            make_request()
        )


@pytest.mark.asyncio
async def test_get_quote_raises_request_error_on_http_error():
    """HTTP errors become AggregatorRequestError."""

    http_client = FakeHttpClient(
        status=500,
        data={
            "error": "Internal Server Error",
        },
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    with pytest.raises(
        AggregatorRequestError
    ):
        await aggregator.get_quote(
            make_request()
        )


@pytest.mark.asyncio
async def test_get_quote_rejects_missing_price_route():
    """Missing priceRoute is treated as invalid response."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    with pytest.raises(
        AggregatorResponseError,
        match="priceRoute",
    ):
        await aggregator.get_quote(
            make_request()
        )


@pytest.mark.asyncio
async def test_get_quote_accepts_optional_requester_address():
    """Requester address can be supplied to Velora."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "priceRoute": {
                "destAmount": "1234567",
            },
        },
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    request = QuoteRequest(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000000,
        token_in_decimals=6,
        token_out_decimals=18,
        requester_address="0xRequester",
    )

    quote = await aggregator.get_quote(
        request
    )

    assert quote.amount_out == 1234567


def test_aggregator_metadata():
    """Velora metadata is exposed correctly."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = VeloraAggregator(
        http_client=http_client,
    )

    assert aggregator.name == "Velora"
    assert aggregator.official_url == "https://velora.xyz"
