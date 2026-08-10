"""
Tests for the aggregator registry.
"""

import pytest

from aggregators.aggregator_interface import AggregatorInterface
from aggregators.oneinch import OneInchAggregator
from aggregators.registry import (
    AggregatorDefinition,
    AggregatorRegistry,
)
from aggregators.uniswap import UniswapAggregator
from aggregators.velora import VeloraAggregator
from aggregators.zero_x import ZeroXAggregator


def test_registry_contains_all_supported_aggregators():
    """All supported aggregators are registered."""

    registry = AggregatorRegistry()

    assert registry.names() == (
        "1inch",
        "0x",
        "Uniswap",
        "Velora",
    )


@pytest.mark.parametrize(
    "name, implementation, requires_api_key",
    [
        ("1inch", OneInchAggregator, True),
        ("0x", ZeroXAggregator, True),
        ("Uniswap", UniswapAggregator, True),
        ("Velora", VeloraAggregator, False),
    ],
)
def test_registry_definition(
    name,
    implementation,
    requires_api_key,
):
    """Registered metadata is correct."""

    registry = AggregatorRegistry()

    definition = registry.get(name)

    assert isinstance(
        definition,
        AggregatorDefinition,
    )

    assert definition.name == name
    assert definition.implementation is implementation
    assert (
        definition.requires_api_key
        is requires_api_key
    )


def test_registry_contains():
    """Registry correctly reports registered names."""

    registry = AggregatorRegistry()

    assert registry.contains("1inch")
    assert registry.contains("0x")
    assert registry.contains("Uniswap")
    assert registry.contains("Velora")

    assert not registry.contains("Unknown")


def test_registry_get_unknown_raises_error():
    """Unknown aggregator cannot be retrieved."""

    registry = AggregatorRegistry()

    with pytest.raises(
        KeyError,
        match="Unknown aggregator",
    ):
        registry.get("Unknown")


def test_registry_returns_all_definitions():
    """Registry returns all definitions."""

    registry = AggregatorRegistry()

    definitions = registry.all()

    assert len(definitions) == 4

    assert all(
        isinstance(
            definition,
            AggregatorDefinition,
        )
        for definition in definitions
    )


def test_registry_custom_registration():
    """Custom aggregator definitions can be registered."""

    class FakeAggregator(
        AggregatorInterface
    ):
        @property
        def name(self) -> str:
            return "Fake"

        @property
        def official_url(self) -> str:
            return "https://example.com"

        async def get_quote(
            self,
            request,
        ):
            raise NotImplementedError

        async def is_available(self) -> bool:
            return True

    registry = AggregatorRegistry()

    registry.register(
        AggregatorDefinition(
            name="Fake",
            implementation=FakeAggregator,
            requires_api_key=False,
            official_url="https://example.com",
        )
    )

    definition = registry.get("Fake")

    assert definition.name == "Fake"
    assert (
        definition.implementation
        is FakeAggregator
    )
    assert not definition.requires_api_key


def test_registry_rejects_duplicate_registration():
    """Duplicate aggregator names are rejected."""

    registry = AggregatorRegistry()

    existing = registry.get("1inch")

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(existing)


def test_registry_rejects_invalid_definition():
    """Registry rejects objects of the wrong type."""

    registry = AggregatorRegistry()

    with pytest.raises(
        TypeError,
        match="AggregatorDefinition",
    ):
        registry.register("invalid")


def test_registry_rejects_empty_name():
    """Empty aggregator names are rejected."""

    registry = AggregatorRegistry()

    definition = AggregatorDefinition(
        name="   ",
        implementation=OneInchAggregator,
        requires_api_key=True,
        official_url="https://1inch.com",
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        registry.register(definition)


def test_registry_remove():
    """Registered aggregators can be removed."""

    registry = AggregatorRegistry()

    removed = registry.remove("Velora")

    assert removed.name == "Velora"
    assert not registry.contains("Velora")


def test_registry_remove_unknown_raises_error():
    """Removing an unknown aggregator raises an error."""

    registry = AggregatorRegistry()

    with pytest.raises(
        KeyError,
        match="Unknown aggregator",
    ):
        registry.remove("Unknown")
