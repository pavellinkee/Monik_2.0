"""
Scan cycle orchestrator.

Responsibility:
    Execute Stage 2 pending work and Stage 1 scanning according
    to the current application lifecycle.

This module connects:
    CoordinatorRuntime
    ApplicationPipeline

It does not implement API calls.
"""

from __future__ import annotations

from core.application_pipeline import (
    ApplicationPipeline,
)
from core.coordinator_runtime import (
    CoordinatorRuntime,
)
from models.net_profit import NetProfitResult


class ScanCycleOrchestrator:
    """
    Executes one logical application scan cycle.
    """

    def __init__(
        self,
        *,
        runtime: CoordinatorRuntime,
        pipeline: ApplicationPipeline,
    ) -> None:
        if not isinstance(
            runtime,
            CoordinatorRuntime,
        ):
            raise TypeError(
                "runtime must be a CoordinatorRuntime."
            )

        if not isinstance(
            pipeline,
            ApplicationPipeline,
        ):
            raise TypeError(
                "pipeline must be an ApplicationPipeline."
            )

        self._runtime = runtime
        self._pipeline = pipeline

    async def run(
        self,
    ) -> tuple[NetProfitResult, ...]:
        """
        Execute one logical cycle.

        Pending Stage 2 is processed first.

        Then Stage 1 runs and creates new Stage 2 pending work.

        This preserves the meaning of Stage 2 priority without
        making empty Stage 2 requests.
        """

        stage2_results = (
            await self._runtime.run_stage2()
        )

        final_results: list[
            NetProfitResult
        ] = []

        if stage2_results:
            processed = (
                await self._pipeline.process_many(
                    stage2_results
                )
            )

            final_results.extend(
                processed
            )

        await self._runtime.run_stage1()

        return tuple(
            final_results
        )

    async def execute(
        self,
    ) -> tuple[NetProfitResult, ...]:
        """
        Compatibility alias.
        """

        return await self.run()
