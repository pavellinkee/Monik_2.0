"""
Tests for the shared HTTP client manager.

These tests do not make real HTTP requests.
"""

import pytest

from aggregators.http_client import HttpClient
from aggregators.http_client_manager import HttpClientManager


def test_manager_creates_http_client():
    """Manager creates an HTTP client for an aggregator."""

    manager = HttpClientManager()

    client = manager.get_or_create("1inch")

    assert isinstance(
        client,
        HttpClient,
    )


def test_manager_reuses_client_for_same_aggregator():
    """The same aggregator receives the same HTTP client."""

    manager = HttpClientManager()

    first = manager.get_or_create("1inch")
    second = manager.get_or_create("1inch")

    assert first is second


def test_manager_creates_separate_clients_for_different_aggregators():
    """Different aggregators receive different clients."""

    manager = HttpClientManager()

    oneinch = manager.get_or_create("1inch")
    zero_x = manager.get_or_create("0x")

    assert oneinch is not zero_x


def test_manager_keeps_clients_separated_by_name():
    """Each aggregator has its own client entry."""

    manager = HttpClientManager()

    oneinch = manager.get_or_create("1inch")
    zero_x = manager.get_or_create("0x")
    uniswap = manager.get_or_create("Uniswap")
    velora = manager.get_or_create("Velora")

    assert manager.get_or_create("1inch") is oneinch
    assert manager.get_or_create("0x") is zero_x
    assert manager.get_or_create("Uniswap") is uniswap
    assert manager.get_or_create("Velora") is velora


@pytest.mark.asyncio
async def test_manager_start_and_close():
    """Manager starts and closes managed HTTP clients."""

    manager = HttpClientManager()

    client = manager.get_or_create("1inch")

    await manager.start()

    assert client._session is not None

    await manager.close()

    assert client._session is None


@pytest.mark.asyncio
async def test_manager_start_is_idempotent():
    """Starting the manager multiple times is safe."""

    manager = HttpClientManager()

    client = manager.get_or_create("1inch")

    await manager.start()
    first_session = client._session

    await manager.start()
    second_session = client._session

    assert first_session is second_session

    await manager.close()


@pytest.mark.asyncio
async def test_manager_close_is_idempotent():
    """Closing the manager multiple times is safe."""

    manager = HttpClientManager()

    manager.get_or_create("1inch")

    await manager.start()

    await manager.close()
    await manager.close()


def test_manager_can_create_client_after_close():
    """Manager can create/access clients after closing."""

    manager = HttpClientManager()

    first = manager.get_or_create("1inch")

    assert isinstance(
        first,
        HttpClient,
    )


def test_manager_uses_independent_clients_for_each_name():
    """Client identity is determined by aggregator name."""

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
