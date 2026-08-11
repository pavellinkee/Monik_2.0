"""
Graceful shutdown manager.

Responsibility:
    Coordinate application shutdown requests.
"""

from __future__ import annotations

import asyncio


class ShutdownManager:
    """
    Async shutdown signal manager.
    """

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def request_shutdown(
        self,
    ) -> None:
        """
        Request application shutdown.
        """

        self._event.set()

    def is_requested(
        self,
    ) -> bool:
        """
        Return True when shutdown was requested.
        """

        return self._event.is_set()

    async def wait(
        self,
    ) -> None:
        """
        Wait until shutdown is requested.
        """

        await self._event.wait()

    def reset(
        self,
    ) -> None:
        """
        Reset shutdown state.
        """

        self._event.clear()

    def request(
        self,
    ) -> None:
        """
        Compatibility alias.
        """

        self.request_shutdown()
