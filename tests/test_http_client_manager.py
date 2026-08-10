"""
Tests for the shared HTTP client manager.

These tests do not make real HTTP requests.
"""

import pytest

from aggregators.http_client import HttpClient
from aggregators.http_client_manager import (
    HttpClientManager,
)


def test_manager_creates_http_client():
    """Manager creates an HTTP client."""

    manager = HttpClientManager()

    client = manager.get_or_create(
        "1inch"
    )

    assert isinstance(
        client,
        HttpClient,
    )


def test_manager_reuses_client_for_same_aggregator():
    """The same aggregator receives the same client."""

    manager = HttpClientManager()

    first = manager.get_or_create(
        "1inch"
    )

    second = manager.get_or_create(
        "1inch"
    )

    assert first is second


def test_manager_creates_separate_clients():
    """Different aggregators receive separate clients."""

    manager = HttpClientManager()

    oneinch = manager.get_or_create(
        "1inch"
    )

    zero_x = manager.get_or_create(
        "0x"
    )

    assert oneinch is not zero_x


def test_manager_supports_custom_timeout():
    """A client can receive a custom timeout."""

    manager = HttpClientManager()

    client = manager.get_or_create(
        "1inch",
        timeout_seconds=20.0,
    )

    assert isinstance(
        client,
        HttpClient,
    )


def test_manager_supports_custom_connector_limit():
    """A client can receive a custom connector limit."""

    manager = HttpClientManager()

    client = manager.get_or_create(
        "1inch",
        connector_limit=50,
    )

    assert isinstance(
        client,
        HttpClient,
    )


def test_manager_keeps_clients_by_name():
    """Each aggregator name maps to its own client."""

    manager = HttpClientManager()

    names = [
        "1inch",
        "0x",
        "Uniswap",
        "Velora",
    ]

    clients = [
        manager.get_or_create(name)
        for name in names
    ]

    assert len(clients) == 4
    assert len(
        {id(client) for client in clients}
    ) == 4


@pytest.mark.asyncio
async def test_manager_start_all_and_close_all():
    """Manager starts and closes all managed clients."""

    manager = HttpClientManager()

    client = manager.get_or_create(
        "1inch"
    )

    await manager.start_all()

    assert client._session is not None

    await manager.close_all()

    assert client._session is None


@pytest.mark.asyncio
async def test_manager_start_all_is_idempotent():
    """Starting all clients twice is safe."""

    manager = HttpClientManager()

    client = manager.get_or_create(
        "1inch"
    )

    await manager.start_all()

    first_session = client._session

    await manager.start_all()

    second_session = client._session

    assert first_session is second_session

    await manager.close_all()


@pytest.mark.asyncio
async def test_manager_close_all_is_idempotent():
    """Closing all clients twice is safe."""

    manager = HttpClientManager()

    manager.get_or_create(
        "1inch"
    )

    await manager.start_all()

    await manager.close_all()
    await manager.close_all()


@pytest.mark.asyncio
async def test_manager_starts_all_aggregators():
    """All managed clients are started together."""

    manager = HttpClientManager()

    oneinch = manager.get_or_create(
        "1inch"
    )

    zero_x = manager.get_or_create(
        "0x"
    )

    velora = manager.get_or_create(
        "Velora"
    )

    await manager.start_all()

    assert oneinch._session is not None
    assert zero_x._session is not None
    assert velora._session is not None

    await manager.close_all()


def test_manager_default_configuration():
    """Default manager configuration is accepted."""

    manager = HttpClientManager()

    client = manager.get_or_create(
        "1inch"
    )

    assert isinstance(
        client,
        HttpClient,
    )
