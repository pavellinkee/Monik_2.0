"""
Tests for HttpClientManager.
"""

import pytest

from aggregators.http_client import HttpClient
from aggregators.http_client_manager import (
    HttpClientManager,
)


def create_manager() -> HttpClientManager:
    """Create a test manager."""

    return HttpClientManager(
        default_timeout_seconds=10.0,
        default_connector_limit=50,
    )


def test_manager_starts_empty():
    """A new manager contains no clients."""

    manager = create_manager()

    assert len(manager.all()) == 0
    assert manager.names() == ()


def test_manager_creates_client():
    """Manager creates and registers a client."""

    manager = create_manager()

    client = manager.create("1inch")

    assert isinstance(
        client,
        HttpClient,
    )

    assert manager.contains("1inch")
    assert manager.get("1inch") is client


def test_manager_uses_default_configuration():
    """Created clients use manager defaults."""

    manager = create_manager()

    client = manager.create("1inch")

    assert (
        client.timeout_seconds
        == pytest.approx(10.0)
    )

    assert (
        client.connector_limit
        == 50
    )


def test_manager_allows_client_specific_configuration():
    """Individual clients can override defaults."""

    manager = create_manager()

    client = manager.create(
        "1inch",
        timeout_seconds=25.0,
        connector_limit=20,
    )

    assert (
        client.timeout_seconds
        == pytest.approx(25.0)
    )

    assert client.connector_limit == 20


def test_manager_rejects_duplicate_client():
    """Duplicate client names are rejected."""

    manager = create_manager()

    manager.create("1inch")

    with pytest.raises(ValueError):
        manager.create("1inch")


def test_manager_adds_existing_client():
    """An existing HttpClient can be registered."""

    manager = create_manager()

    client = HttpClient(
        timeout_seconds=20.0,
        connector_limit=10,
    )

    manager.add(
        "custom",
        client,
    )

    assert manager.get("custom") is client


def test_manager_rejects_invalid_client():
    """Only HttpClient instances can be registered."""

    manager = create_manager()

    with pytest.raises(TypeError):
        manager.add(
            "invalid",
            object(),
        )


def test_manager_rejects_duplicate_added_client():
    """Adding a duplicate client is rejected."""

    manager = create_manager()

    manager.create("1inch")

    with pytest.raises(ValueError):
        manager.add(
            "1inch",
            HttpClient(),
        )


def test_manager_get_unknown_client_raises():
    """Unknown client names raise KeyError."""

    manager = create_manager()

    with pytest.raises(KeyError):
        manager.get("Unknown")


def test_manager_get_or_create_reuses_existing_client():
    """get_or_create returns an existing client."""

    manager = create_manager()

    first = manager.create("1inch")

    second = manager.get_or_create(
        "1inch",
        timeout_seconds=50.0,
        connector_limit=5,
    )

    assert second is first

    assert (
        second.timeout_seconds
        == pytest.approx(10.0)
    )

    assert second.connector_limit == 50


def test_manager_get_or_create_creates_missing_client():
    """get_or_create creates a missing client."""

    manager = create_manager()

    client = manager.get_or_create(
        "0x",
        timeout_seconds=30.0,
        connector_limit=25,
    )

    assert isinstance(
        client,
        HttpClient,
    )

    assert manager.contains("0x")

    assert (
        client.timeout_seconds
        == pytest.approx(30.0)
    )

    assert client.connector_limit == 25


def test_manager_returns_names():
    """Manager returns registered client names."""

    manager = create_manager()

    manager.create("1inch")
    manager.create("0x")
    manager.create("Velora")

    assert manager.names() == (
        "1inch",
        "0x",
        "Velora",
    )


def test_manager_returns_all_clients():
    """Manager returns all registered clients."""

    manager = create_manager()

    first = manager.create("1inch")
    second = manager.create("0x")

    clients = manager.all()

    assert clients == (
        first,
        second,
    )


def test_manager_remove_returns_client():
    """Removing a client returns the client."""

    manager = create_manager()

    client = manager.create("1inch")

    removed = manager.remove("1inch")

    assert removed is client
    assert not manager.contains("1inch")


def test_manager_remove_unknown_client_raises():
    """Removing an unknown client raises KeyError."""

    manager = create_manager()

    with pytest.raises(KeyError):
        manager.remove("Unknown")


def test_manager_rejects_empty_name():
    """Empty client names are rejected."""

    manager = create_manager()

    with pytest.raises(ValueError):
        manager.create("")


def test_manager_rejects_whitespace_name():
    """Whitespace-only names are rejected."""

    manager = create_manager()

    with pytest.raises(ValueError):
        manager.create("   ")


def test_manager_rejects_non_string_name():
    """Client names must be strings."""

    manager = create_manager()

    with pytest.raises(TypeError):
        manager.create(123)


def test_manager_configuration_properties():
    """Manager exposes its default configuration."""

    manager = HttpClientManager(
        default_timeout_seconds=20.0,
        default_connector_limit=75,
    )

    assert (
        manager.default_timeout_seconds
        == pytest.approx(20.0)
    )

    assert (
        manager.default_connector_limit
        == 75
    )


def test_manager_rejects_invalid_timeout():
    """Default timeout must be positive."""

    with pytest.raises(ValueError):
        HttpClientManager(
            default_timeout_seconds=0
        )

    with pytest.raises(ValueError):
        HttpClientManager(
            default_timeout_seconds=-1
        )


def test_manager_rejects_invalid_connector_limit():
    """Default connector limit must be positive."""

    with pytest.raises(ValueError):
        HttpClientManager(
            default_connector_limit=0
        )

    with pytest.raises(ValueError):
        HttpClientManager(
            default_connector_limit=-1
        )


@pytest.mark.asyncio
async def test_start_all_starts_every_client():
    """start_all opens every registered client."""

    manager = create_manager()

    first = manager.create("1inch")
    second = manager.create("0x")
    third = manager.create("Velora")

    await manager.start_all()

    try:
        assert first.is_open
        assert second.is_open
        assert third.is_open

    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_close_all_closes_every_client():
    """close_all closes every registered client."""

    manager = create_manager()

    first = manager.create("1inch")
    second = manager.create("0x")

    await manager.start_all()

    assert first.is_open
    assert second.is_open

    await manager.close_all()

    assert not first.is_open
    assert not second.is_open


@pytest.mark.asyncio
async def test_start_all_is_idempotent():
    """Starting all clients multiple times is safe."""

    manager = create_manager()

    client = manager.create("1inch")

    await manager.start_all()

    first_session = client._session

    await manager.start_all()

    second_session = client._session

    try:
        assert first_session is second_session
        assert client.is_open

    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_close_all_is_idempotent():
    """Closing all clients multiple times is safe."""

    manager = create_manager()

    client = manager.create("1inch")

    await manager.start_all()

    await manager.close_all()
    await manager.close_all()

    assert not client.is_open


@pytest.mark.asyncio
async def test_manager_async_context_manager():
    """Manager works as an async context manager."""

    manager = create_manager()

    manager.create("1inch")
    manager.create("0x")

    async with manager:
        assert manager.get("1inch").is_open
        assert manager.get("0x").is_open

    assert not manager.get("1inch").is_open
    assert not manager.get("0x").is_open


@pytest.mark.asyncio
async def test_removed_client_is_not_managed():
    """Removed clients are no longer managed."""

    manager = create_manager()

    client = manager.create("1inch")

    await manager.start_all()

    assert client.is_open

    removed = manager.remove("1inch")

    assert removed is client
    assert not manager.contains("1inch")

    await manager.close_all()

    # The manager no longer owns this client.
    # Therefore its session remains open until explicitly closed.
    assert client.is_open

    await client.close()

    assert not client.is_open
