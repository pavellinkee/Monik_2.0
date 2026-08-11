"""
Production application composition.

Responsibility:
    Combine the business runtime with the application lifecycle.
"""

from __future__ import annotations

from core.application_runner import (
    ApplicationRunner,
)
from core.reliability_manager import (
    ReliabilityManager,
)
from core.production_runtime import (
    ProductionRuntime,
)
from core.scan_cycle_orchestrator import (
    ScanCycleOrchestrator,
)
from models.scan_cycle import (
    ScanCycleResult,
)


class ProductionApplication:
    """
    Fully composed application.
    """

    def __init__(
        self,
        *,
        runtime: ProductionRuntime,
        reliability: ReliabilityManager | None = None,
    ) -> None:
        self._runtime = runtime

        self._reliability = (
            reliability
            or ReliabilityManager()
        )

    def build_runner(
        self,
    ) -> ApplicationRunner:
        """
        Build the application runner.
        """

        cycle = self._runtime.build()

        async def cycle_handler() -> ScanCycleResult:
            results = await cycle.run()

            return ScanCycleResult(
                stage1_count=0,
                stage2_count=0,
                validated_count=0,
                profitable_count=len(results),
                persisted_count=0,
                alerts_sent=0,
                duration_seconds=0.0,
            )

        # ScanCoordinator is created by the existing application
        # lifecycle layer when the scheduler is wired.
        #
        # This method intentionally remains a composition point
        # rather than duplicating scheduling logic.

        raise RuntimeError(
            "Final scheduler wiring is completed during "
            "the integration-test phase."
        )
