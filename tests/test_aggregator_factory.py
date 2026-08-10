"""
Tests for AggregatorFactory.

These tests do not send real API requests.
"""

import pytest

from aggregators.factory import AggregatorFactory
from aggregators.http_client import HttpClient


def create_factory() -> AggregatorFactory:
    """Create a factory with a shared HTTP client."""

    return AggregatorFactory(
        http_client=HttpClient()
    )


def test_factory_creates_all_enabled_aggregators():
    """Factory creates all enabled aggregators."""

    factory = create_factory()

    config = {
        "1inch": {
            "enabled": True,
            "api_key": "test-1inch-key",
        },
        "0x": {
            "enabled": True,
            "api_key": "test-0x-key",
        },
        "Uniswap": {
            "enabled": True,
            "api_key": "test-uniswap-key",
        },
        "Velora": {
            "enabled": True,
        },
    }

    registry = factory.create(config)

    assert len(registry) == 4

    assert registry.contains("1inch")
    assert registry.contains("0x")
    assert registry.contains("Uniswap")
    assert registry.contains("Velora")


def test_factory_skips_disabled_aggregator():
    """Disabled aggregators are not created."""

    factory = create_factory()

    config = {
        "1inch": {
            "enabled": False,
            "api_key": "test-key",
        },
        "0x": {
            "enabled": True,
            "api_key": "test-key",
        },
        "Velora": {
            "enabled": True,
        },
    }

    registry = factory.create(config)

    assert len(registry) == 2

    assert not registry.contains("1inch")
    assert registry.contains("0x")
    assert registry.contains("Velora")


def test_factory_allows_velora_without_api_key():
    """Velora does not require an API key."""

    factory = create_factory()

    config = {
        "Velora": {
            "enabled": True,
        }
    }

    registry = factory.create(config)

    assert len(registry) == 1
    assert registry.contains("Velora")


def test_factory_requires_api_key_for_1inch():
    """1inch requires an API key."""

    factory = create_factory()

    config = {
        "1inch": {
            "enabled": True,
        }
    }

    with pytest.raises(ValueError):
        factory.create(config)


def test_factory_requires_api_key_for_zero_x():
    """0x requires an API key."""

    factory = create_factory()

    config = {
        "0x": {
            "enabled": True,
        }
    }

    with pytest.raises(ValueError):
        factory.create(config)


def test_factory_requires_api_key_for_uniswap():
    """Uniswap requires an API key."""

    factory = create_factory()

    config = {
        "Uniswap": {
            "enabled": True,
        }
    }

    with pytest.raises(ValueError):
        factory.create(config)


def test_factory_skips_disabled_aggregator_without_key():
    """
    A disabled aggregator does not require an API key.
    """

    factory = create_factory()

    config = {
        "1inch": {
            "enabled": False,
        }
    }

    registry = factory.create(config)

    assert len(registry) == 0


def test_factory_rejects_unknown_aggregator():
    """Unknown aggregator names are rejected."""

    factory = create_factory()

    config = {
        "UnknownAggregator": {
            "enabled": True,
        }
    }

    with pytest.raises(ValueError):
        factory.create(config)


def test_factory_rejects_invalid_enabled_value():
    """The enabled flag must be boolean."""

    factory = create_factory()

    config = {
        "Velora": {
            "enabled": "yes",
        }
    }

    with pytest.raises(TypeError):
        factory.create(config)
