"""
Application bootstrap.

Responsibility:
    Construct the application dependency graph.

This module is the composition root.

Business components must not instantiate infrastructure
dependencies internally.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from core.application_context import (
    ApplicationContext,
)
from core.application_pipeline import (
    ApplicationPipeline,
)
from core.application_runner import (
    ApplicationRunner,
)
from core.opportunity_persistence import (
    OpportunityPersistence,
)
from core.opportunity_validator import (
    OpportunityValidator,
)
from core.profitability_filter import (
    ProfitabilityFilter,
)
from core.reliability_manager import (
    ReliabilityManager,
)
from core.scan_coordinator import (
    ScanCoordinator,
)
from core.scanner_engine import ScannerEngine
from core.telegram_alert_manager import (
    TelegramAlertManager,
)


class ApplicationBootstrap:
    """
    Application composition root.

    All infrastructure dependencies are supplied from outside.
    """

    def __init__(
        self,
        *,
        scanner_engine: ScannerEngine,
        aggregator_engine,
        stage3_runner,
        stage1_runner,
        stage2_runner,
        persistence: OpportunityPersistence | None = None,
        telegram: TelegramAlertManager | None = None,
        reliability: ReliabilityManager | None = None,
        stage1_interval_seconds: float = 600.0,
        stage2_max_concurrent_checks: int = 1,
    ) -> None:
        self._scanner_engine = scanner_engine
        self._aggregator_engine = aggregator_engine

        self._stage3_runner = stage3_runner

        self._stage1_runner = stage1_runner
        self._stage2_runner = stage2_runner

        self._persistence = persistence
        self._telegram = telegram

        self._reliability = (
            reliability
            or ReliabilityManager()
        )

        self._stage1_interval_seconds = (
            stage1_interval_seconds
        )

        self._stage2_max_concurrent_checks = (
            stage2_max_concurrent_checks
        )

    def build(self) -> ApplicationContext:
        """
        Build the complete application context.
        """

        validator = OpportunityValidator()

        profitability_filter = (
            ProfitabilityFilter()
        )

        pipeline = ApplicationPipeline(
            stage3_runner=self._stage3_runner,
            validator=validator,
            profitability_filter=(
                profitability_filter
            ),
            persistence=self._persistence,
            telegram=self._telegram,
        )

        coordinator = ScanCoordinator(
            stage1_runner=self._stage1_runner,
            stage2_runner=self._stage2_runner,
            stage1_interval_seconds=(
                self._stage1_interval_seconds
            ),
            stage2_max_concurrent_checks=(
                self._stage2_max_concurrent_checks
            ),
            stage2_priority=True,
        )

        async def cycle_handler():
            await coordinator.run_cycle()

            return await self._run_pipeline_cycle(
                pipeline
            )

        runner = ApplicationRunner(
            coordinator=coordinator,
            cycle_handler=cycle_handler,
            reliability=self._reliability,
        )

        return ApplicationContext(
            scanner_engine=self._scanner_engine,
            aggregator_engine=self._aggregator_engine,
            coordinator=coordinator,
            pipeline=pipeline,
            runner=runner,
        )

    async def _run_pipeline_cycle(
        self,
        pipeline: ApplicationPipeline,
    ):
        """
        Execute the business pipeline.

        The concrete Stage 2 result acquisition remains injected
        by the caller and will be connected to the existing
        scanner implementation during final integration.
        """

        return await self._stage3_runner(None)
