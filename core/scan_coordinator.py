"""
Scan coordinator.

Responsibility:
    Coordinate Stage 1 and Stage 2 execution according to the
    configured scanner policy.

The coordinator does NOT:
    - make HTTP requests;
    - implement rate limiting;
    - implement aggregator queues;
    - calculate arbitrage;
    - calculate gas;
    - calculate profitability;
    - access the database;
    - send Telegram messages.

Those responsibilities remain in their dedicated modules.

Scheduling rules:
    1. Stage 2 has priority when pending work exists.
    2. Stage 1 may run in parallel with Stage 2 when they use
       independent aggregator queues.
    3. Stage 2 concurrency is bounded by configuration.
    4. Stage 1 interval is measured from the start of a run.
    5. The coordinator never bypasses AggregatorEngine queues.
    6. A failed cycle must not terminate the coordinator.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScanCycleResult:
    """
    Immutable result of one coordinator cycle.
    """

    stage1_completed: bool
    stage2_completed: bool
    stage1_duration_seconds: float
    stage2_duration_seconds: float


class ScanCoordinator:
    """
    Coordinates Stage 1 and Stage 2 scheduling.

    The actual scanner implementations are injected as callables.
    This keeps the coordinator independent from ScannerEngine and
    Stage2Engine concrete implementations.
    """

    def __init__(
        self,
        stage1_runner: Callable[
            [],
            Awaitable[Any],
        ],
        stage2_runner: Callable[
            [],
            Awaitable[Any],
        ],
        *,
        stage1_interval_seconds: float = 600.0,
        stage2_max_concurrent_checks: int = 1,
        stage2_priority: bool = True,
    ) -> None:
        if not callable(stage1_runner):
            raise TypeError(
                "stage1_runner must be callable."
            )

        if not callable(stage2_runner):
            raise TypeError(
                "stage2_runner must be callable."
            )

        if stage1_interval_seconds <= 0:
            raise ValueError(
                "stage1_interval_seconds must be "
                "greater than zero."
            )

        if stage2_max_concurrent_checks <= 0:
            raise ValueError(
                "stage2_max_concurrent_checks must be "
                "greater than zero."
            )

        self._stage1_runner = stage1_runner
        self._stage2_runner = stage2_runner

        self._stage1_interval_seconds = (
            float(stage1_interval_seconds)
        )

        self._stage2_semaphore = asyncio.Semaphore(
            stage2_max_concurrent_checks
        )

        self._stage2_priority = stage2_priority

        self._stop_event = asyncio.Event()

        self._stage1_task: asyncio.Task[Any] | None = None
        self._stage2_tasks: set[
            asyncio.Task[Any]
        ] = set()

    @property
    def stage1_interval_seconds(self) -> float:
        """
        Return the configured Stage 1 interval.
        """
        return self._stage1_interval_seconds

    @property
    def stage2_priority(self) -> bool:
        """
        Return whether Stage 2 has scheduling priority.
        """
        return self._stage2_priority

    def stop(self) -> None:
        """
        Request coordinator shutdown.
        """
        self._stop_event.set()

    async def run_stage1(self) -> Any:
        """
        Execute one Stage 1 run.

        The Stage 1 runner itself is responsible for the actual
        parallel token and aggregator scanning.
        """
        started = time.monotonic()

        try:
            return await self._stage1_runner()
        finally:
            elapsed = (
                time.monotonic() - started
            )

            if elapsed < self._stage1_interval_seconds:
                await asyncio.sleep(
                    self._stage1_interval_seconds
                    - elapsed
                )

    async def run_stage2(
        self,
    ) -> Any:
        """
        Execute one Stage 2 run under the configured concurrency
        limit.
        """
        async with self._stage2_semaphore:
            return await self._stage2_runner()

    async def submit_stage2(
        self,
    ) -> asyncio.Task[Any]:
        """
        Submit a Stage 2 task.

        Stage 2 tasks are bounded by the semaphore and therefore
        cannot exceed the configured concurrency.
        """
        task = asyncio.create_task(
            self.run_stage2()
        )

        self._stage2_tasks.add(task)

        task.add_done_callback(
            self._stage2_tasks.discard
        )

        return task

    async def run_cycle(
        self,
        *,
        run_stage2: bool = True,
    ) -> ScanCycleResult:
        """
        Run one coordinated scan cycle.

        Stage 2 is submitted before Stage 1 when priority is
        enabled.

        Stage 1 is then allowed to execute without bypassing
        aggregator-level queues.
        """

        stage1_completed = False
        stage2_completed = False

        stage1_duration = 0.0
        stage2_duration = 0.0

        stage2_started = time.monotonic()

        if (
            run_stage2
            and self._stage2_priority
        ):
            try:
                await self.run_stage2()
                stage2_completed = True
            finally:
                stage2_duration = (
                    time.monotonic()
                    - stage2_started
                )

        stage1_started = time.monotonic()

        try:
            await self.run_stage1()
            stage1_completed = True
        finally:
            stage1_duration = (
                time.monotonic()
                - stage1_started
            )

        if (
            run_stage2
            and not self._stage2_priority
        ):
            stage2_started = time.monotonic()

            try:
                await self.run_stage2()
                stage2_completed = True
            finally:
                stage2_duration = (
                    time.monotonic()
                    - stage2_started
                )

        return ScanCycleResult(
            stage1_completed=stage1_completed,
            stage2_completed=stage2_completed,
            stage1_duration_seconds=(
                stage1_duration
            ),
            stage2_duration_seconds=(
                stage2_duration
            ),
        )

    async def run_forever(
        self,
    ) -> None:
        """
        Run the coordinator continuously.

        The coordinator continues after individual cycle failures.
        """
        while not self._stop_event.is_set():
            try:
                await self.run_cycle()

            except asyncio.CancelledError:
                raise

            except Exception:
                # The coordinator must remain alive.
                # Diagnostics are handled by the dedicated
                # diagnostic layer.
                pass

    async def shutdown(self) -> None:
        """
        Stop the coordinator and wait for active Stage 2 tasks.
        """
        self.stop()

        tasks = tuple(
            self._stage2_tasks
        )

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        self._stage2_tasks.clear()

        self._stage1_task = None

    # -----------------------------------------------------------------
    # Compatibility interfaces
    # -----------------------------------------------------------------

    async def run(
        self,
    ) -> None:
        """
        Legacy compatibility alias for run_forever().
        """
        await self.run_forever()

    async def start(
        self,
    ) -> None:
        """
        Compatibility alias for run_forever().
        """
        await self.run_forever()
