"""
Scan task executor.

Responsibility:
    Execute concrete scan tasks with bounded concurrency.

The executor does NOT:
    - make HTTP requests itself;
    - implement aggregator queues;
    - implement rate limiting;
    - calculate profitability;
    - access the database.

Actual aggregator communication remains inside ScannerEngine
and AggregatorEngine.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from models.scan_plan import ScanPlan, ScanTask


class ScanTaskExecutor:
    """
    Executes scan tasks with bounded concurrency.
    """

    def __init__(
        self,
        task_runner: Callable[
            [ScanTask],
            Awaitable[object],
        ],
        *,
        max_concurrent_tasks: int = 1,
    ) -> None:
        if not callable(task_runner):
            raise TypeError(
                "task_runner must be callable."
            )

        if max_concurrent_tasks <= 0:
            raise ValueError(
                "max_concurrent_tasks must be "
                "greater than zero."
            )

        self._task_runner = task_runner

        self._semaphore = asyncio.Semaphore(
            max_concurrent_tasks
        )

    async def execute_task(
        self,
        task: ScanTask,
    ) -> object:
        """
        Execute one task under the concurrency limit.
        """

        if not isinstance(
            task,
            ScanTask,
        ):
            raise TypeError(
                "task must be a ScanTask."
            )

        async with self._semaphore:
            return await self._task_runner(
                task
            )

    async def execute(
        self,
        plan: ScanPlan,
    ) -> tuple[object, ...]:
        """
        Execute every task in the plan.

        Result order matches the order of plan.tasks.
        """

        if not isinstance(
            plan,
            ScanPlan,
        ):
            raise TypeError(
                "plan must be a ScanPlan."
            )

        if plan.is_empty:
            return ()

        tasks = tuple(
            asyncio.create_task(
                self.execute_task(task)
            )
            for task in plan.tasks
        )

        return tuple(
            await asyncio.gather(*tasks)
        )

    async def run(
        self,
        plan: ScanPlan,
    ) -> tuple[object, ...]:
        """
        Legacy compatibility alias for execute().
        """
        return await self.execute(plan)
