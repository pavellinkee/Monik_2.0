"""
Application context.

Responsibility:
    Hold initialized application services.

The context does not create services itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.application_pipeline import (
    ApplicationPipeline,
)
from core.application_runner import (
    ApplicationRunner,
)
from core.aggregator_engine import AggregatorEngine
from core.scan_coordinator import ScanCoordinator
from core.scanner_engine import ScannerEngine


@dataclass
class ApplicationContext:
    """
    Runtime application dependency container.
    """

    scanner_engine: ScannerEngine
    aggregator_engine: AggregatorEngine
    coordinator: ScanCoordinator
    pipeline: ApplicationPipeline
    runner: ApplicationRunner

    def stop(self) -> None:
        """
        Request application shutdown.
        """
        self.runner.stop()

    async def shutdown(self) -> None:
        """
        Gracefully shut down all managed runtime components.
        """
        await self.runner.shutdown()
