"""
Tests for AggregatorRegistry.

These tests do not send real API requests.
"""

import pytest

from aggregators.registry import AggregatorRegistry
from aggregators.oneinch import OneInchAggregator
from aggregators.uniswap import UniswapAggregator
from aggregators.velora import VeloraAggregator
from aggregators.zero_x import ZeroXAggregator


class FakeHttpClient:
    """Fake HTTP client for registry tests."""

    async def get(
        self,
        url,
        *,
        headers=None,
        params=None,
    ):
        """Return an empty successful response."""
        return 200, {}

    async def post(
        self,
        url,
        *,
        headers=None,
        json=None,
        params=None,
    ):
        """Return an empty successful response."""
        return 200, {}


def create_adapters():
    """Create all supported aggregator adapters."""

    http_client = FakeHttpClient()

    return [
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


def test_registry_registers_all_aggregators():
    """Registry stores all supported aggregators."""

    registry = AggregatorRegistry(
        create_adapters()
    )

    assert len(registry) == 4

    assert registry.contains("1inch")
    assert registry.contains("0x")
    assert registry.contains("Uniswap")
    assert registry.contains("Velora")


def test_registry_returns_aggregator_by_name():
    """Registry returns the correct adapter."""

    registry = AggregatorRegistry(
        create_adapters()
    )

    oneinch = registry.get("1inch")
    uniswap = registry.get("Uniswap")

    assert oneinch.name == "1inch"
    assert uniswap.name == "Uniswap"


def test_registry_returns_all_aggregators():
    """Registry returns all registered adapters."""

    registry = AggregatorRegistry(
        create_adapters()
    )

    aggregators = registry.all()

    assert len(aggregators) == 4

    assert {
        aggregator.name
        for aggregator in aggregators
    } == {
        "1inch",
        "0x",
        "Uniswap",
        "Velora",
    }


def test_registry_returns_names():
    """Registry returns registered names."""

    registry = AggregatorRegistry(
        create_adapters()
    )

    assert registry.names() == (
        "1inch",
        "0x",
        "Uniswap",
        "Velora",
    )


def test_registry_returns_official_url():
    """Registry exposes official aggregator URLs."""

    registry = AggregatorRegistry(
        create_adapters()
    )

    assert (
        registry.official_url("1inch")
        == "https://1inch.com"
    )

    assert (
        registry.official_url("Uniswap")
        == "https://app.uniswap.org"
    )

    assert (
        registry.official_url("Velora")
        == "https://velora.xyz"
    )


def test_registry_rejects_duplicate_aggregator():
    """Duplicate aggregator names are rejected."""

    adapters = create_adapters()

    registry = AggregatorRegistry(
        adapters
    )

    with pytest.raises(ValueError):
        registry.register(
            adapters[0]
        )


def test_registry_rejects_unknown_aggregator():
    """Unknown aggregator names raise KeyError."""

    registry = AggregatorRegistry(
        create_adapters()
    )

    with pytest.raises(KeyError):
        registry.get("Unknown")


def test_registry_rejects_invalid_object():
    """Registry accepts only AggregatorInterface objects."""

    registry = AggregatorRegistry([])

    with pytest.raises(TypeError):
        registry.register(object())
