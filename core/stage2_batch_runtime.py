"""
Stage 2 batch runtime.

Responsibility:
    Convert pending Stage 1 results into one Stage 2 batch.

The actual Stage 2 engine remains responsible for:
    - reverse quote construction;
    - aggregator requests;
    - aggregator queues;
    - rate limiting.
"""

from __future__ import annotations

from collections.abc import Iterable

from core.stage_runtime import StageRuntime
from core.stage2_pending_queue import (
    Stage2PendingQueue,
)


class Stage2BatchRuntime:
    """
    Runs Stage 2 against pending Stage 1 work.
    """

    def __init__(
        self,
        *,
        stage_runtime: StageRuntime,
        pending_queue: Stage2PendingQueue | None = None,
    ) -> None:
        if not isinstance(
            stage_runtime,
            StageRuntime,
        ):
            raise TypeError(
                "stage_runtime must be a StageRuntime."
            )

        self._stage_runtime = stage_runtime

        self._pending_queue = (
            pending_queue
            or Stage2PendingQueue()
        )

    @property
    def pending_queue(
        self,
    ) -> Stage2PendingQueue:
        """
        Return the pending Stage 2 queue.
        """

        return self._pending_queue

    async def submit(
        self,
        results: Iterable,
    ) -> int:
        """
        Submit Stage 1 results for Stage 2.
        """

        return await self._pending_queue.put_many(
            results
        )

    async def run_pending(
        self,
    ):
        """
        Drain the current pending Stage 2 batch and execute it.
        """

        batch = self._pending_queue.clear()

        if not batch:
            return ()

        return await self._stage_runtime.run_stage2(
            batch
        )

    async def run(
        self,
        results: Iterable | None = None,
    ):
        """
        Run Stage 2.

        When results are supplied they are submitted first.
        """

        if results is not None:
            await self.submit(results)

        return await self.run_pending()

    async def execute(
        self,
        results: Iterable | None = None,
    ):
        """
        Compatibility alias.
        """

        return await self.run(results)
