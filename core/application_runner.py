"""
Application runner.

Responsibility:
    Run the scanner application continuously.

The runner owns lifecycle orchestration only.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from core.reliability_manager import (
    ReliabilityManager,
)
from core.scan_coordinator import (
    ScanCoordinator,
)
from models.scan_cycle import ScanCycleResult


CycleHandler = Callable[
    [],
    Awaitable[ScanCycleResult],
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

        if not callable(cycle_handler):
            raise TypeError(
                "cycle_handler must be callable."
            )

        self._coordinator = coordinator
        self._cycle_handler = cycle_handler

        self._reliability = (
            reliability
            or ReliabilityManager()
        )

        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """
        Request application shutdown.
        """
        self._stop_event.set()
        self._coordinator.stop()

    async def run_once(
        self,
    ) -> ScanCycleResult:
        """
        Execute one application cycle.
        """

        started = time.monotonic()

        try:
            result = await self._cycle_handler()

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

        finally:
            _ = time.monotonic() - started

    async def run_forever(
        self,
    ) -> None:
        """
        Run application cycles until stopped.
        """

        while not self._stop_event.is_set():
            try:
                await self.run_once()

            except asyncio.CancelledError:
                raise

            except Exception:
                await asyncio.sleep(1)

    async def shutdown(self) -> None:
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
