"""
Tests for the aggregator factory.

These tests do not make real HTTP requests.
"""

from types import SimpleNamespace

import pytest

from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.errors import (
    AggregatorConfigurationError,
)
from aggregators.factory import AggregatorFactory
from aggregators.http_client_manager import (
    HttpClientManager,
)
from aggregators.oneinch import OneInchAggregator
from aggregators.registry import (
    AggregatorRegistry,
)
from aggregators.uniswap import UniswapAggregator
from aggregators.velora import VeloraAggregator
from aggregators.zero_x import ZeroXAggregator


class FakeHttpClient:
    """Fake HTTP client shared by factory-created adapters."""


class FakeHttpClientManager:
    """Fake HTTP client manager for factory tests."""

    def __init__(self):
        self.clients = {}
        self.calls = []

    def get_or_create(
        self,
        name: str,
    ):
        """Return one stable client per aggregator."""

        self.calls.append(name)

        if name not in self.clients:
            self.clients[name] = FakeHttpClient()

        return self.clients[name]


def make_config(
    *,
    enabled: bool = True,
    api_key: str | None = "test-api-key",
):
    """Create a minimal aggregator configuration."""

    return SimpleNamespace(
        enabled=enabled,
        api_key=api_key,
    )


def make_factory():
    """Create a factory with a fake HTTP manager."""

    manager = FakeHttpClientManager()

    factory = AggregatorFactory(
        http_client_manager=manager,
    )

    return factory, manager


@pytest.mark.parametrize(
    "name, expected_type",
    [
        ("1inch", OneInchAggregator),
        ("0x", ZeroXAggregator),
        ("Uniswap", UniswapAggregator),
        ("Velora", VeloraAggregator),
    ],
)
def test_factory_creates_supported_aggregator(
    name,
    expected_type,
):
    """Factory creates the correct implementation."""

    factory, manager = make_factory()

    config = make_config(
        api_key=(
            None
            if name == "Velora"
            else "test-api-key"
        )
    )

    aggregator = factory.create(
        name,
        config,
    )

    assert isinstance(
        aggregator,
        expected_type,
    )

    assert isinstance(
        aggregator,
        AggregatorInterface,
    )

    assert manager.calls == [name]


@pytest.mark.parametrize(
    "name",
    [
        "1inch",
        "0x",
        "Uniswap",
    ],
)
def test_factory_requires_api_key(
    name,
):
    """API-key-based aggregators reject missing keys."""

    factory, _ = make_factory()

    with pytest.raises(
        AggregatorConfigurationError,
        match="requires an API key",
    ):
        factory.create(
            name,
            make_config(
                api_key=None
            ),
        )


def test_factory_allows_velora_without_api_key():
    """Velora can be created without an API key."""

    factory, _ = make_factory()

    aggregator = factory.create(
        "Velora",
        make_config(
            api_key=None
        ),
    )

    assert isinstance(
        aggregator,
        VeloraAggregator,
    )


def test_factory_rejects_disabled_aggregator():
    """Disabled aggregators cannot be created."""

    factory, _ = make_factory()

    with pytest.raises(
        AggregatorConfigurationError,
        match="disabled",
    ):
        factory.create(
            "1inch",
            make_config(
                enabled=False
            ),
        )


def test_factory_rejects_unknown_aggregator():
    """Unknown aggregators are rejected."""

    factory, _ = make_factory()

    with pytest.raises(
        KeyError,
        match="Unknown aggregator",
    ):
        factory.create(
            "Unknown",
            make_config(),
        )


def test_factory_rejects_config_without_enabled():
    """Configuration must contain enabled."""

    factory, _ = make_factory()

    config = SimpleNamespace(
        api_key="test-api-key"
    )

    with pytest.raises(
        AggregatorConfigurationError,
        match="enabled",
    ):
        factory.create(
            "1inch",
            config,
        )


def test_factory_reuses_http_client_for_same_aggregator():
    """Factory requests one client for repeated creation."""

    factory, manager = make_factory()

    config = make_config()

    first = factory.create(
        "1inch",
        config,
    )

    second = factory.create(
        "1inch",
        config,
    )

    assert first is not second

    assert manager.clients["1inch"] is not None

    assert manager.calls == [
        "1inch",
        "1inch",
    ]

    assert (
        first._http_client
        is second._http_client
    )


def test_factory_create_enabled():
    """Factory creates all enabled aggregators."""

    factory, manager = make_factory()

    configs = {
        "1inch": make_config(
            enabled=True,
            api_key="one-inch-key",
        ),
        "0x": make_config(
            enabled=True,
            api_key="zero-x-key",
        ),
        "Uniswap": make_config(
            enabled=False,
            api_key="uniswap-key",
        ),
        "Velora": make_config(
            enabled=True,
            api_key=None,
        ),
    }

    result = factory.create_enabled(
        configs
    )

    assert set(result.keys()) == {
        "1inch",
        "0x",
        "Velora",
    }

    assert isinstance(
        result["1inch"],
        OneInchAggregator,
    )

    assert isinstance(
        result["0x"],
        ZeroXAggregator,
    )

    assert isinstance(
        result["Velora"],
        VeloraAggregator,
    )

    assert "Uniswap" not in result

    assert manager.calls == [
        "1inch",
        "0x",
        "Velora",
    ]


def test_factory_create_enabled_rejects_unknown():
    """create_enabled rejects unknown aggregators."""

    factory, _ = make_factory()

    configs = {
        "Unknown": make_config(),
    }

    with pytest.raises(
        AggregatorConfigurationError,
        match="Unknown aggregator",
    ):
        factory.create_enabled(
            configs
        )


def test_factory_create_enabled_requires_one_enabled():
    """At least one aggregator must be enabled."""

    factory, _ = make_factory()

    configs = {
        "1inch": make_config(
            enabled=False,
        ),
        "Velora": make_config(
            enabled=False,
            api_key=None,
        ),
    }

    with pytest.raises(
        AggregatorConfigurationError,
        match="No enabled aggregators",
    ):
        factory.create_enabled(
            configs
        )


def test_factory_exposes_registry():
    """Factory exposes its registry."""

    factory, _ = make_factory()

    assert isinstance(
        factory.registry,
        AggregatorRegistry,
    )


def test_factory_accepts_custom_registry():
    """Factory can use an externally supplied registry."""

    registry = AggregatorRegistry()

    manager = FakeHttpClientManager()

    factory = AggregatorFactory(
        http_client_manager=manager,
        registry=registry,
    )

    assert factory.registry is registry


def test_factory_exposes_http_client_manager():
    """Factory exposes its HTTP client manager."""

    factory, manager = make_factory()

    assert (
        factory.http_client_manager
        is manager
    )
