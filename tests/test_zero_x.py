"""
Tests for the 0x Swap API v2 aggregator adapter.

These tests do not make real requests to the 0x API.
"""

import pytest

from aggregators.errors import (
    AggregatorConfigurationError,
    AggregatorRateLimitError,
    AggregatorRequestError,
    AggregatorResponseError,
)
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest
from aggregators.zero_x import ZeroXAggregator


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
    requester_address: str | None = "0xRequester",
) -> QuoteRequest:
    """Create a standard 0x test request."""

    return QuoteRequest(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000000,
        requester_address=requester_address,
    )


@pytest.mark.asyncio
async def test_get_quote_returns_normalized_quote():
    """0x response is converted into Quote."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "buyAmount": "1234567",
            "sellAmount": "1000000000",
            "liquidityAvailable": True,
            "totalNetworkFee": "4200000000000000",
            "blockNumber": "12345678",
            "transaction": {
                "gas": "185000",
            },
            "route": {
                "fills": [
                    {
                        "source": "Uniswap_V3",
                    },
                    {
                        "source": "Curve",
                    },
                ],
            },
        },
    )

    aggregator = ZeroXAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    quote = await aggregator.get_quote(
        make_request()
    )

    assert isinstance(quote, Quote)

    assert quote.aggregator == "0x"
    assert quote.chain_id == 137

    assert quote.token_in == "0xTokenIn"
    assert quote.token_out == "0xTokenOut"

    assert quote.amount_in == 1000000000
    assert quote.amount_out == 1234567

    assert quote.gas_estimate == 185000

    assert quote.gas_cost_native is not None
    assert str(quote.gas_cost_native) == "0.0042"

    assert quote.price_impact is None
    assert quote.route == "Uniswap_V3 → Curve"
    assert quote.timestamp == "12345678"


@pytest.mark.asyncio
async def test_get_quote_requires_requester_address():
    """0x requires a taker/requester address."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = ZeroXAggregator(
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

    aggregator = ZeroXAggregator(
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

    aggregator = ZeroXAggregator(
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
async def test_get_quote_rejects_missing_buy_amount():
    """Missing buyAmount is treated as invalid response."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "liquidityAvailable": True,
        },
    )

    aggregator = ZeroXAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    with pytest.raises(
        AggregatorResponseError,
        match="buyAmount",
    ):
        await aggregator.get_quote(
            make_request()
        )


def test_missing_api_key_is_rejected():
    """0x requires an API key."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    with pytest.raises(
        AggregatorConfigurationError
    ):
        ZeroXAggregator(
            http_client=http_client,
            api_key="",
        )


def test_aggregator_metadata():
    """0x metadata is exposed correctly."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = ZeroXAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    assert aggregator.name == "0x"
    assert aggregator.official_url == "https://0x.org"
