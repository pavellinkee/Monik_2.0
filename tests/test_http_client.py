"""
Tests for the shared asynchronous HTTP client.
"""

import asyncio

import aiohttp
import pytest

from aggregators.http_client import (
    HttpClient,
    HttpRequestError,
)


@pytest.mark.asyncio
async def test_client_starts_closed():
    """A new client does not have an open session."""

    client = HttpClient()

    assert client.is_open is False

    await client.close()


@pytest.mark.asyncio
async def test_client_start_opens_session():
    """start() creates an open HTTP session."""

    client = HttpClient()

    await client.start()

    try:
        assert client.is_open is True

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_start_is_idempotent():
    """Calling start() multiple times reuses the same session."""

    client = HttpClient()

    await client.start()

    first_session = client._session

    await client.start()

    second_session = client._session

    try:
        assert first_session is second_session
        assert client.is_open is True

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_close_is_idempotent():
    """Calling close() multiple times is safe."""

    client = HttpClient()

    await client.start()

    await client.close()
    await client.close()

    assert client.is_open is False


@pytest.mark.asyncio
async def test_client_can_restart_after_close():
    """A closed client can be started again."""

    client = HttpClient()

    await client.start()

    first_session = client._session

    await client.close()

    assert client.is_open is False

    await client.start()

    second_session = client._session

    try:
        assert first_session is not second_session
        assert client.is_open is True

    finally:
        await client.close()


def test_invalid_timeout_is_rejected():
    """Timeout must be positive."""

    with pytest.raises(ValueError):
        HttpClient(
            timeout_seconds=0
        )

    with pytest.raises(ValueError):
        HttpClient(
            timeout_seconds=-1
        )


def test_invalid_connector_limit_is_rejected():
    """Connection limit must be positive."""

    with pytest.raises(ValueError):
        HttpClient(
            connector_limit=0
        )

    with pytest.raises(ValueError):
        HttpClient(
            connector_limit=-1
        )


def test_configuration_properties():
    """Configured values are exposed correctly."""

    client = HttpClient(
        timeout_seconds=25.0,
        connector_limit=50,
    )

    assert (
        client.timeout_seconds
        == pytest.approx(25.0)
    )

    assert (
        client.connector_limit
        == 50
    )


@pytest.mark.asyncio
async def test_get_requires_valid_url():
    """GET rejects an empty URL."""

    client = HttpClient()

    with pytest.raises(ValueError):
        await client.get("")

    await client.close()


@pytest.mark.asyncio
async def test_post_requires_valid_url():
    """POST rejects an empty URL."""

    client = HttpClient()

    with pytest.raises(ValueError):
        await client.post("")

    await client.close()


@pytest.mark.asyncio
async def test_get_returns_status_and_json(
    unused_tcp_port,
):
    """GET returns HTTP status and decoded JSON."""

    async def handler(request):
        return aiohttp.web.json_response(
            {
                "success": True,
                "value": 123,
            }
        )

    app = aiohttp.web.Application()

    app.router.add_get(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.get(
            f"http://127.0.0.1:{unused_tcp_port}/test"
        )

        assert status == 200

        assert data == {
            "success": True,
            "value": 123,
        }

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_post_returns_status_and_json(
    unused_tcp_port,
):
    """POST returns HTTP status and decoded JSON."""

    async def handler(request):
        body = await request.json()

        return aiohttp.web.json_response(
            {
                "received": body,
            }
        )

    app = aiohttp.web.Application()

    app.router.add_post(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.post(
            f"http://127.0.0.1:{unused_tcp_port}/test",
            json={
                "amount": 100,
                "token": "USDT",
            },
        )

        assert status == 200

        assert data == {
            "received": {
                "amount": 100,
                "token": "USDT",
            }
        }

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_get_passes_headers_and_params(
    unused_tcp_port,
):
    """GET forwards headers and query parameters."""

    async def handler(request):
        return aiohttp.web.json_response(
            {
                "token": request.headers.get(
                    "X-Test-Header"
                ),
                "amount": request.query.get(
                    "amount"
                ),
            }
        )

    app = aiohttp.web.Application()

    app.router.add_get(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.get(
            f"http://127.0.0.1:{unused_tcp_port}/test",
            headers={
                "X-Test-Header": "test-value",
            },
            params={
                "amount": "1000",
            },
        )

        assert status == 200

        assert data == {
            "token": "test-value",
            "amount": "1000",
        }

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_post_passes_headers_and_params(
    unused_tcp_port,
):
    """POST forwards headers, parameters and JSON body."""

    async def handler(request):
        body = await request.json()

        return aiohttp.web.json_response(
            {
                "header": request.headers.get(
                    "X-Test-Header"
                ),
                "amount": request.query.get(
                    "amount"
                ),
                "body": body,
            }
        )

    app = aiohttp.web.Application()

    app.router.add_post(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.post(
            f"http://127.0.0.1:{unused_tcp_port}/test",
            headers={
                "X-Test-Header": "test-value",
            },
            params={
                "amount": "500",
            },
            json={
                "token": "USDT",
            },
        )

        assert status == 200

        assert data == {
            "header": "test-value",
            "amount": "500",
            "body": {
                "token": "USDT",
            },
        }

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_non_json_response_is_returned_as_text(
    unused_tcp_port,
):
    """Non-JSON responses are returned as text."""

    async def handler(request):
        return aiohttp.web.Response(
            text="plain response",
            content_type="text/plain",
        )

    app = aiohttp.web.Application()

    app.router.add_get(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.get(
            f"http://127.0.0.1:{unused_tcp_port}/test"
        )

        assert status == 200
        assert data == "plain response"

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_empty_response_returns_none(
    unused_tcp_port,
):
    """Empty responses return None."""

    async def handler(request):
        return aiohttp.web.Response(
            status=204
        )

    app = aiohttp.web.Application()

    app.router.add_get(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.get(
            f"http://127.0.0.1:{unused_tcp_port}/test"
        )

        assert status == 204
        assert data is None

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_http_error_status_is_preserved(
    unused_tcp_port,
):
    """
    HTTP error statuses are returned to the caller.

    The shared HTTP client does not interpret aggregator-specific
    statuses such as 401, 429 or 500.
    """

    async def handler(request):
        return aiohttp.web.json_response(
            {
                "error": "rate limited",
            },
            status=429,
        )

    app = aiohttp.web.Application()

    app.router.add_get(
        "/test",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient()

    try:
        status, data = await client.get(
            f"http://127.0.0.1:{unused_tcp_port}/test"
        )

        assert status == 429

        assert data == {
            "error": "rate limited",
        }

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_timeout_becomes_http_request_error(
    unused_tcp_port,
):
    """Request timeout is normalized to HttpRequestError."""

    async def handler(request):
        await asyncio.sleep(0.2)

        return aiohttp.web.json_response(
            {
                "success": True,
            }
        )

    app = aiohttp.web.Application()

    app.router.add_get(
        "/slow",
        handler,
    )

    runner = aiohttp.web.AppRunner(app)

    await runner.setup()

    site = aiohttp.web.TCPSite(
        runner,
        "127.0.0.1",
        unused_tcp_port,
    )

    await site.start()

    client = HttpClient(
        timeout_seconds=0.05
    )

    try:
        with pytest.raises(
            HttpRequestError,
            match="timed out",
        ):
            await client.get(
                f"http://127.0.0.1:{unused_tcp_port}/slow"
            )

    finally:
        await client.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_connection_error_becomes_http_request_error():
    """Connection failures are normalized."""

    client = HttpClient(
        timeout_seconds=0.5
    )

    try:
        with pytest.raises(
            HttpRequestError,
            match="HTTP request failed",
        ):
            await client.get(
                "http://127.0.0.1:1"
            )

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_async_context_manager():
    """HttpClient works as an async context manager."""

    async with HttpClient() as client:
        assert client.is_open is True

    assert client.is_open is False
