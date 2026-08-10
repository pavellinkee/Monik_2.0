"""
Tests for the Uniswap Trading API aggregator adapter.

These tests do not make real requests to the Uniswap API.
"""

from decimal import Decimal

import pytest

from aggregators.errors import (
    AggregatorConfigurationError,
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest
from aggregators.uniswap import UniswapAggregator


class FakeHttpClient:
    """Fake HTTP client used for unit tests."""

    def __init__(
        self,
        status: int,
        data,
    ):
        self.status = status
        self.data = data

    async def post(
        self,
        url: str,
        *,
        headers=None,
        json=None,
        params=None,
    ):
        """Return the predefined fake response."""

        return self.status, self.data


def make_request(
    requester_address: str | None = "0xRequester",
) -> QuoteRequest:
    """Create a standard Uniswap test request."""

    return QuoteRequest(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000000,
        requester_address=requester_address,
    )


@pytest.mark.asyncio
async def test_get_quote_returns_normalized_quote():
    """Uniswap response is converted into Quote."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "quote": {
                "output": {
                    "amount": "1234567",
                },
            },
            "routing": "CLASSIC",
            "requestId": "request-123",
        },
    )

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    quote = await aggregator.get_quote(
        make_request()
    )

    assert isinstance(quote, Quote)

    assert quote.aggregator == "Uniswap"
    assert quote.chain_id == 137

    assert quote.token_in == "0xTokenIn"
    assert quote.token_out == "0xTokenOut"

    assert quote.amount_in == 1000000000
    assert quote.amount_out == 1234567

    assert quote.gas_estimate is None
    assert quote.gas_cost_native is None

    assert quote.price_impact is None
    assert quote.route == "CLASSIC"
    assert quote.timestamp == "request-123"


@pytest.mark.asyncio
async def test_get_quote_requires_requester_address():
    """Uniswap requires a swapper/requester address."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    with pytest.raises(
        AggregatorConfigurationError,
        match="requester_address",
    ):
        await aggregator.get_quote(
            make_request(
                requester_address=None
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

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
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

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    with pytest.raises(
        AggregatorRequestError
    ):
        await aggregator.get_quote(
            make_request()
        )


@pytest.mark.asyncio
async def test_get_quote_rejects_missing_quote():
    """Missing quote object is treated as invalid response."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "routing": "CLASSIC",
        },
    )

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    with pytest.raises(
        AggregatorResponseError,
        match="quote",
    ):
        await aggregator.get_quote(
            make_request()
        )


@pytest.mark.asyncio
async def test_get_quote_supports_order_info_output():
    """UniswapX orderInfo output can be normalized."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "quote": {
                "orderInfo": {
                    "outputs": [
                        {
                            "startAmount": "9876543",
                        }
                    ],
                },
            },
            "routing": "DUTCH_V2",
            "requestId": "request-456",
        },
    )

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    quote = await aggregator.get_quote(
        make_request()
    )

    assert quote.amount_out == 9876543
    assert quote.route == "DUTCH_V2"
    assert quote.timestamp == "request-456"


def test_missing_api_key_is_rejected():
    """Uniswap requires an API key."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    with pytest.raises(
        AggregatorConfigurationError
    ):
        UniswapAggregator(
            http_client=http_client,
            api_key="",
        )


def test_aggregator_metadata():
    """Uniswap metadata is exposed correctly."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = UniswapAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    assert aggregator.name == "Uniswap"
    assert aggregator.official_url == "https://uniswap.org"
