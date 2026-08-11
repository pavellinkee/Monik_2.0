"""
Coordinator runtime adapter.

Responsibility:
    Connect the existing ScanCoordinator with the real Stage 1
    and Stage 2 engines.

Important scheduling rule:

    Stage 2 priority applies only when Stage 2 work is pending.

Therefore:
    - first cycle creates Stage 1 work;
    - Stage 1 results become pending Stage 2 work;
    - next scheduling opportunity gives Stage 2 priority;
    - Stage 1 can continue independently when allowed.

The adapter does not bypass AggregatorEngine queues.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from core.stage_runtime import StageRuntime
from core.stage2_pending_queue import (
    Stage2PendingQueue,
)


class CoordinatorRuntime:
    """
    Runtime bridge between ScanCoordinator and scanner stages.
    """

    def __init__(
        self,
        *,
        stage_runtime: StageRuntime,
        chain_ids: tuple[int, ...],
        scan_amounts_usdt: tuple[Decimal, ...],
        max_tokens: int | None = None,
    ) -> None:
        if not isinstance(
            stage_runtime,
            StageRuntime,
        ):
            raise TypeError(
                "stage_runtime must be a StageRuntime."
            )

        if not chain_ids:
            raise ValueError(
                "At least one chain must be configured."
            )

        if not scan_amounts_usdt:
            raise ValueError(
                "At least one scan amount must be configured."
            )

        self._stage_runtime = stage_runtime

        self._chain_ids = tuple(
            chain_ids
        )

        self._scan_amounts_usdt = tuple(
            scan_amounts_usdt
        )

        self._max_tokens = max_tokens

        self._pending_stage2 = (
            Stage2PendingQueue()
        )

        self._last_stage1_results: tuple[
            Any,
            ...
        ] = ()

        self._last_stage2_results: tuple[
            Any,
            ...
        ] = ()

        self._lock = asyncio.Lock()

    @property
    def pending_stage2_count(
        self,
    ) -> int:
        """
        Return number of Stage 2 results waiting to be processed.
        """

        return self._pending_stage2.qsize()

    async def run_stage1(
        self,
    ):
        """
        Execute configured Stage 1 scans.

        Each chain/amount combination is delegated to the
        existing ScannerEngine.
        """

        all_results = []

        for chain_id in self._chain_ids:
            for amount in self._scan_amounts_usdt:
                results = (
                    await self._stage_runtime.run_stage1(
                        chain_id=chain_id,
                        amount_usdt=amount,
                        max_tokens=self._max_tokens,
                    )
                )

                all_results.extend(
                    results
                )

        stage1_results = tuple(
            all_results
        )

        async with self._lock:
            self._last_stage1_results = (
                stage1_results
            )

        await self._pending_stage2.put_many(
            stage1_results
        )

        return stage1_results

    async def run_stage2(
        self,
    ):
        """
        Process currently pending Stage 2 work.

        If no Stage 2 work is pending, this method returns an
        empty tuple instead of making useless API requests.
        """

        if self._pending_stage2.empty():
            return ()

        batch = self._pending_stage2.clear()

        results = (
            await self._stage_runtime.run_stage2(
                batch
            )
        )

        stage2_results = tuple(
            results
        )

        async with self._lock:
            self._last_stage2_results = (
                stage2_results
            )

        return stage2_results

    async def stage1(
        self,
    ):
        """
        Compatibility alias.
        """

        return await self.run_stage1()

    async def stage2(
        self,
    ):
        """
        Compatibility alias.
        """

        return await self.run_stage2()

    async def get_last_stage1_results(
        self,
    ) -> tuple:
        """
        Return the most recent Stage 1 results.
        """

        async with self._lock:
            return self._last_stage1_results

    async def get_last_stage2_results(
        self,
    ) -> tuple:
        """
        Return the most recent Stage 2 results.
        """

        async with self._lock:
            return self._last_stage2_results

    async def shutdown(
        self,
    ) -> None:
        """
        Clear pending Stage 2 work during shutdown.
        """

        self._pending_stage2.clear()
