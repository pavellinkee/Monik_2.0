"""
Tests for the 1inch aggregator adapter.

These tests do not make real requests to the 1inch API.
They verify that the adapter correctly converts a 1inch response
into our common Quote model and correctly handles API errors.
"""

from decimal import Decimal

import pytest

from aggregators.errors import (
    AggregatorRateLimitError,
    AggregatorRequestError,
)
from aggregators.oneinch import OneInchAggregator
from aggregators.quote import Quote


class FakeHttpClient:
    """Fake HTTP client used for unit tests."""

    def __init__(
        self,
        status: int,
        data: dict,
    ):
        self.status = status
        self.data = data

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict | None = None,
    ):
        """Return the predefined fake response."""
        return self.status, self.data


@pytest.mark.asyncio
async def test_get_quote_returns_normalized_quote():
    """1inch response is converted into Quote."""

    http_client = FakeHttpClient(
        status=200,
        data={
            "dstAmount": "1234567",
            "gas": "185000",
            "gasCost": "4200000000000000",
            "priceImpact": "0.25",
            "protocols": [
                [
                    [
                        {
                            "name": "UNISWAP_V3",
                        }
                    ]
                ]
            ],
            "timestamp": "1750000000",
        },
    )

    aggregator = OneInchAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    quote = await aggregator.get_quote(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000000,
    )

    assert isinstance(quote, Quote)

    assert quote.aggregator == "1inch"
    assert quote.chain_id == 137

    assert quote.token_in == "0xTokenIn"
    assert quote.token_out == "0xTokenOut"

    assert quote.amount_in == 1000000000
    assert quote.amount_out == 1234567

    assert quote.gas_estimate == 185000
    assert quote.gas_cost_native == Decimal(
        "0.0042"
    )

    assert quote.price_impact == Decimal(
        "0.25"
    )

    assert quote.route == "UNISWAP_V3"
    assert quote.timestamp == "1750000000"


@pytest.mark.asyncio
async def test_get_quote_raises_rate_limit_error():
    """HTTP 429 is converted into AggregatorRateLimitError."""

    http_client = FakeHttpClient(
        status=429,
        data={
            "error": "Too Many Requests",
        },
    )

    aggregator = OneInchAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    with pytest.raises(
        AggregatorRateLimitError
    ):
        await aggregator.get_quote(
            chain_id=137,
            token_in="0xTokenIn",
            token_out="0xTokenOut",
            amount=1000000000,
        )


@pytest.mark.asyncio
async def test_get_quote_raises_request_error_on_http_error():
    """HTTP errors are converted into AggregatorRequestError."""

    http_client = FakeHttpClient(
        status=500,
        data={
            "error": "Internal Server Error",
        },
    )

    aggregator = OneInchAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    with pytest.raises(
        AggregatorRequestError
    ):
        await aggregator.get_quote(
            chain_id=137,
            token_in="0xTokenIn",
            token_out="0xTokenOut",
            amount=1000000000,
        )


def test_aggregator_metadata():
    """1inch metadata is exposed correctly."""

    http_client = FakeHttpClient(
        status=200,
        data={},
    )

    aggregator = OneInchAggregator(
        http_client=http_client,
        api_key="test-api-key",
    )

    assert aggregator.name == "1inch"
    assert aggregator.official_url == "https://1inch.com"
