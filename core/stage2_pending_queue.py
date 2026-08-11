"""
Pending Stage 2 queue.

Responsibility:
    Store Stage 1 results waiting for Stage 2 processing.

The queue:
    - does not make API requests;
    - does not calculate profitability;
    - does not access SQL;
    - does not implement aggregator queues.

Stage 2 priority is applied to work that is actually pending.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable


class Stage2PendingQueue:
    """
    Async-safe FIFO queue for pending Stage 2 work.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()

    async def put(
        self,
        result,
    ) -> None:
        """
        Add one Stage 1 result to the pending queue.
        """

        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        await self._queue.put(
            result
        )

    async def put_many(
        self,
        results: Iterable,
    ) -> int:
        """
        Add multiple Stage 1 results.
        """

        count = 0

        for result in results:
            await self.put(result)
            count += 1

        return count

    async def get(
        self,
    ):
        """
        Wait for and return one pending result.
        """

        return await self._queue.get()

    def get_nowait(
        self,
    ):
        """
        Return one result without waiting.
        """

        return self._queue.get_nowait()

    def task_done(
        self,
    ) -> None:
        """
        Mark one queued result as processed.
        """

        self._queue.task_done()

    async def join(
        self,
    ) -> None:
        """
        Wait until all queued work is completed.
        """

        await self._queue.join()

    def qsize(
        self,
    ) -> int:
        """
        Return current queue size.
        """

        return self._queue.qsize()

    def empty(
        self,
    ) -> bool:
        """
        Return True when no pending work exists.
        """

        return self._queue.empty()

    def clear(
        self,
    ) -> tuple:
        """
        Drain currently pending work.

        Intended primarily for graceful shutdown.
        """

        items = []

        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            items.append(item)
            self._queue.task_done()

        return tuple(items)

    async def add(
        self,
        result,
    ) -> None:
        """
        Legacy compatibility alias.
        """

        await self.put(result)
