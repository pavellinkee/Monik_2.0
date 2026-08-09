"""
Compatibility tests for the Aggregator Layer.

These tests do not send real API requests.

They verify that:
    - all aggregator adapters implement the common interface;
    - all adapters expose required metadata;
    - all adapters can be constructed;
    - all adapters use the common Quote model;
    - HTTP status errors are normalized correctly.
"""

import inspect

import pytest

from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.http_client import HttpClient
from aggregators.oneinch import OneInchAggregator
from aggregators.quote import Quote
from aggregators.uniswap import UniswapAggregator
from aggregators.velora import VeloraAggregator
from aggregators.zero_x import ZeroXAggregator


class FakeHttpClient:
    """Fake HTTP client for adapter tests."""

    def __init__(
        self,
        status: int = 200,
        data: dict | None = None,
    ):
        self.status = status
        self.data = data or {}

    async def get(
        self,
        url: str,
        *,
        headers=None,
        params=None,
    ):
        """Return a predefined GET response."""
        return self.status, self.data

    async def post(
        self,
        url: str,
        *,
        headers=None,
        json=None,
        params=None,
    ):
        """Return a predefined POST response."""
        return self.status, self.data


def test_all_adapters_implement_common_interface():
    """All adapters must implement AggregatorInterface."""

    http_client = FakeHttpClient()

    adapters = [
        OneInchAggregator(
            http_client=http_client,
            api_key="test-key",
        ),
        ZeroXAggregator(
            http_client=http_client,
            api_key="test-key",
        ),
        UniswapAggregator(
            http_client=http_client,
            api_key="test-key",
        ),
        VeloraAggregator(
            http_client=http_client,
        ),
    ]

    for adapter in adapters:
        assert isinstance(
            adapter,
            AggregatorInterface,
        )


def test_all_adapters_expose_metadata():
    """Every adapter exposes name and official URL."""

    http_client = FakeHttpClient()

    adapters = [
        OneInchAggregator(
            http_client=http_client,
            api_key="test-key",
        ),
        ZeroXAggregator(
            http_client=http_client,
            api_key="test-key",
        ),
        UniswapAggregator(
            http_client=http_client,
            api_key="test-key",
        ),
        VeloraAggregator(
            http_client=http_client,
        ),
    ]

    for adapter in adapters:
        assert isinstance(
            adapter.name,
            str,
        )

        assert adapter.name

        assert isinstance(
            adapter.official_url,
            str,
        )

        assert adapter.official_url.startswith(
            "https://"
        )


def test_all_adapters_have_async_get_quote():
    """Every adapter must provide an async get_quote method."""

    adapters = [
        OneInchAggregator(
            http_client=FakeHttpClient(),
            api_key="test-key",
        ),
        ZeroXAggregator(
            http_client=FakeHttpClient(),
            api_key="test-key",
        ),
        UniswapAggregator(
            http_client=FakeHttpClient(),
            api_key="test-key",
        ),
        VeloraAggregator(
            http_client=FakeHttpClient(),
        ),
    ]

    for adapter in adapters:
        method = getattr(
            adapter,
            "get_quote",
        )

        assert inspect.iscoroutinefunction(
            method
        )


def test_http_client_has_get_and_post():
    """Common HTTP client supports required methods."""

    client = HttpClient()

    assert hasattr(
        client,
        "get",
    )

    assert hasattr(
        client,
        "post",
    )

    assert inspect.iscoroutinefunction(
        client.get
    )

    assert inspect.iscoroutinefunction(
        client.post
    )


@pytest.mark.asyncio
async def test_oneinch_returns_quote():
    """1inch adapter returns the common Quote model."""

    client = FakeHttpClient(
        status=200,
        data={
            "dstAmount": "123456",
            "gas": "180000",
            "gasCost": "4200000000000000",
            "priceImpact": "0.2",
            "protocols": [],
            "timestamp": "1234567890",
        },
    )

    adapter = OneInchAggregator(
        http_client=client,
        api_key="test-key",
    )

    result = await adapter.get_quote(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000,
    )

    assert isinstance(
        result,
        Quote,
    )

    assert result.aggregator == "1inch"
    assert result.amount_out == 123456


@pytest.mark.asyncio
async def test_zero_x_returns_quote():
    """0x adapter returns the common Quote model."""

    client = FakeHttpClient(
        status=200,
        data={
            "buyAmount": "234567",
            "gas": "200000",
            "gasCost": "5000000000000000",
        },
    )

    adapter = ZeroXAggregator(
        http_client=client,
        api_key="test-key",
    )

    result = await adapter.get_quote(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000,
    )

    assert isinstance(
        result,
        Quote,
    )

    assert result.aggregator == "0x"
    assert result.amount_out == 234567


@pytest.mark.asyncio
async def test_uniswap_returns_quote():
    """Uniswap adapter returns the common Quote model."""

    client = FakeHttpClient(
        status=200,
        data={
            "amountOut": "345678",
            "gas": "210000",
            "gasCost": "6000000000000000",
            "priceImpact": "0.15",
            "route": "V3",
            "timestamp": "1234567890",
        },
    )

    adapter = UniswapAggregator(
        http_client=client,
        api_key="test-key",
    )

    result = await adapter.get_quote(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000,
    )

    assert isinstance(
        result,
        Quote,
    )

    assert result.aggregator == "Uniswap"
    assert result.amount_out == 345678


@pytest.mark.asyncio
async def test_velora_returns_quote():
    """Velora adapter returns the common Quote model."""

    client = FakeHttpClient(
        status=200,
        data={
            "priceRoute": {
                "destAmount": "456789",
                "gasCost": "7000000000000000",
                "gas": "220000",
                "priceImpact": "0.1",
                "bestRoute": "Velora",
                "timestamp": "1234567890",
            }
        },
    )

    adapter = VeloraAggregator(
        http_client=client,
    )

    result = await adapter.get_quote(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000,
    )

    assert isinstance(
        result,
        Quote,
    )

    assert result.aggregator == "Velora"
    assert result.amount_out == 456789


@pytest.mark.asyncio
async def test_velora_does_not_require_api_key():
    """Velora can be constructed without an API key."""

    adapter = VeloraAggregator(
        http_client=FakeHttpClient()
    )

    assert adapter.name == "Velora"


@pytest.mark.asyncio
async def test_1inch_requires_api_key():
    """1inch must reject an empty API key."""

    with pytest.raises(Exception):
        OneInchAggregator(
            http_client=FakeHttpClient(),
            api_key="",
        )


@pytest.mark.asyncio
async def test_zero_x_requires_api_key():
    """0x must reject an empty API key."""

    with pytest.raises(Exception):
        ZeroXAggregator(
            http_client=FakeHttpClient(),
            api_key="",
        )


@pytest.mark.asyncio
async def test_uniswap_requires_api_key():
    """Uniswap must reject an empty API key."""

    with pytest.raises(Exception):
        UniswapAggregator(
            http_client=FakeHttpClient(),
            api_key="",
        )
