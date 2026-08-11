"""
Application runner.

Responsibility:
    Run the scanner application continuously.

The runner owns lifecycle orchestration only.

It does NOT:
    - schedule Stage 1/Stage 2 itself;
    - make aggregator requests;
    - calculate profitability;
    - access SQL;
    - send Telegram messages.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from core.reliability_manager import (
    ReliabilityManager,
)
from core.scan_coordinator import (
    ScanCoordinator,
)
from models.scan_cycle import (
    ScanCycleResult as ApplicationScanCycleResult,
)


CycleHandler = Callable[
    [],
    Awaitable[Any],
]


class ApplicationRunner:
    """
    Production application lifecycle runner.
    """

    def __init__(
        self,
        *,
        coordinator: ScanCoordinator,
        cycle_handler: CycleHandler,
        reliability: ReliabilityManager | None = None,
    ) -> None:
        if not isinstance(
            coordinator,
            ScanCoordinator,
        ):
            raise TypeError(
                "coordinator must be a ScanCoordinator."
            )

        if not callable(
            cycle_handler
        ):
            raise TypeError(
                "cycle_handler must be callable."
            )

        self._coordinator = coordinator

        self._cycle_handler = (
            cycle_handler
        )

        self._reliability = (
            reliability
            or ReliabilityManager()
        )

        self._stop_event = asyncio.Event()

    @property
    def coordinator(
        self,
    ) -> ScanCoordinator:
        """
        Return the scheduler.
        """

        return self._coordinator

    def stop(
        self,
    ) -> None:
        """
        Request application shutdown.
        """

        self._stop_event.set()

        self._coordinator.stop()

    async def run_once(
        self,
    ) -> ApplicationScanCycleResult:
        """
        Execute one application cycle.
        """

        started = time.monotonic()

        try:
            raw_result = (
                await self._cycle_handler()
            )

            result = self._normalize_result(
                raw_result,
                duration_seconds=(
                    time.monotonic()
                    - started
                ),
            )

            await self._reliability.mark_healthy(
                "application",
                "Scan cycle completed.",
            )

            return result

        except asyncio.CancelledError:
            raise

        except Exception as exc:
            await self._reliability.report_error(
                "application",
                exc,
            )

            raise

    async def run_forever(
        self,
    ) -> None:
        """
        Run application cycles until stopped.

        A failed cycle does not terminate the application.
        """

        while not self._stop_event.is_set():
            try:
                await self.run_once()

            except asyncio.CancelledError:
                raise

            except Exception:
                await asyncio.sleep(1)

    async def shutdown(
        self,
    ) -> None:
        """
        Gracefully shut down the application.
        """

        self.stop()

        await self._coordinator.shutdown()

    async def run(
        self,
    ) -> None:
        """
        Legacy compatibility alias.
        """

        await self.run_forever()

    @staticmethod
    def _normalize_result(
        raw_result: Any,
        *,
        duration_seconds: float,
    ) -> ApplicationScanCycleResult:
        """
        Normalize coordinator/pipeline output into the public
        application cycle model.
        """

        # ---------------------------------------------------------
        # Coordinator result + profitable results
        # ---------------------------------------------------------

        if (
            isinstance(
                raw_result,
                tuple,
            )
            and len(raw_result) == 2
        ):
            coordinator_result = raw_result[0]
            profitable_results = raw_result[1]

            stage1_completed = bool(
                getattr(
                    coordinator_result,
                    "stage1_completed",
                    False,
                )
            )

            stage2_completed = bool(
                getattr(
                    coordinator_result,
                    "stage2_completed",
                    False,
                )
            )

            stage1_count = (
                1
                if stage1_completed
                else 0
            )

            stage2_count = (
                1
                if stage2_completed
                else 0
            )

            profitable_count = len(
                tuple(
                    profitable_results
                )
            )

            return ApplicationScanCycleResult(
                stage1_count=stage1_count,
                stage2_count=stage2_count,
                validated_count=(
                    profitable_count
                ),
                profitable_count=(
                    profitable_count
                ),
                persisted_count=0,
                alerts_sent=0,
                duration_seconds=(
                    duration_seconds
                ),
            )

        # ---------------------------------------------------------
        # Existing application result
        # ---------------------------------------------------------

        if isinstance(
            raw_result,
            ApplicationScanCycleResult,
        ):
            return raw_result

        # ---------------------------------------------------------
        # Coordinator-only result
        # ---------------------------------------------------------

        return ApplicationScanCycleResult(
            stage1_count=int(
                bool(
                    getattr(
                        raw_result,
                        "stage1_completed",
                        False,
                    )
                )
            ),
            stage2_count=int(
                bool(
                    getattr(
                        raw_result,
                        "stage2_completed",
                        False,
                    )
                )
            ),
            validated_count=0,
            profitable_count=0,
            persisted_count=0,
            alerts_sent=0,
            duration_seconds=(
                duration_seconds
            ),
        )
