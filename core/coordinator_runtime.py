"""
Coordinator runtime adapter.

Responsibility:
    Provide zero-argument runners required by ScanCoordinator
    while keeping the real scan configuration inside the runtime.

Stage 2 receives the pending Stage 1 results from the latest
Stage 1 execution.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from core.full_scan_cycle import FullScanCycle


class CoordinatorRuntime:
    """
    Bridges FullScanCycle and ScanCoordinator.
    """

    def __init__(
        self,
        cycle: FullScanCycle,
    ) -> None:
        if not isinstance(
            cycle,
            FullScanCycle,
        ):
            raise TypeError(
                "cycle must be a FullScanCycle."
            )

        self._cycle = cycle

        self._stage1_results = ()
        self._lock = asyncio.Lock()

    async def run_stage1(
        self,
    ):
        """
        Execute Stage 1 and retain its results for Stage 2.

        This method intentionally delegates the actual work to
        StageRuntime.
        """

        stage1_results = []

        for chain_id in self._cycle._chain_ids:
            for amount in self._cycle._amounts:
                results = (
                    await self._cycle._stage_runtime.run_stage1(
                        chain_id=chain_id,
                        amount_usdt=amount,
                        max_tokens=self._cycle._max_tokens,
                    )
                )

                stage1_results.extend(
                    results
                )

        async with self._lock:
            self._stage1_results = tuple(
                stage1_results
            )

        return self._stage1_results

    async def run_stage2(
        self,
    ):
        """
        Execute Stage 2 for the latest Stage 1 results.
        """

        async with self._lock:
            stage1_results = self._stage1_results

        if not stage1_results:
            return ()

        return await self._cycle._stage_runtime.run_stage2(
            stage1_results
        )

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
