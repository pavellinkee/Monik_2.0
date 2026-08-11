"""
Application bootstrap.

The ScanCoordinator is the only scheduler.

This bootstrap:
    - wires Stage 1;
    - wires Stage 2;
    - captures completed Stage 2 results;
    - sends those results into ApplicationPipeline;
    - preserves legacy constructor interfaces.

It does NOT create a second scheduler.
"""

from __future__ import annotations

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
    Composition root for the scanner application.
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
        stage2_priority: bool = True,
    ) -> None:
        if not isinstance(
            scanner_engine,
            ScannerEngine,
        ):
            raise TypeError(
                "scanner_engine must be a ScannerEngine."
            )

        if aggregator_engine is None:
            raise ValueError(
                "aggregator_engine cannot be None."
            )

        if not callable(
            stage3_runner
        ):
            raise TypeError(
                "stage3_runner must be callable."
            )

        if not callable(
            stage1_runner
        ):
            raise TypeError(
                "stage1_runner must be callable."
            )

        if not callable(
            stage2_runner
        ):
            raise TypeError(
                "stage2_runner must be callable."
            )

        self._scanner_engine = (
            scanner_engine
        )

        self._aggregator_engine = (
            aggregator_engine
        )

        self._stage3_runner = (
            stage3_runner
        )

        self._stage1_runner = (
            stage1_runner
        )

        self._stage2_runner = (
            stage2_runner
        )

        self._persistence = persistence
        self._telegram = telegram

        self._reliability = (
            reliability
            or ReliabilityManager()
        )

        self._stage1_interval_seconds = (
            float(
                stage1_interval_seconds
            )
        )

        self._stage2_max_concurrent_checks = (
            int(
                stage2_max_concurrent_checks
            )
        )

        self._stage2_priority = bool(
            stage2_priority
        )

    def build(
        self,
    ) -> ApplicationContext:
        """
        Build the complete application context.
        """

        validator = (
            OpportunityValidator()
        )

        profitability_filter = (
            ProfitabilityFilter()
        )

        pipeline = ApplicationPipeline(
            stage3_runner=(
                self._stage3_runner
            ),
            validator=validator,
            profitability_filter=(
                profitability_filter
            ),
            persistence=self._persistence,
            telegram=self._telegram,
        )

        latest_stage2_results = ()

        async def stage2_runner_wrapper():
            nonlocal latest_stage2_results

            result = await self._stage2_runner()

            if result is None:
                latest_stage2_results = ()
                return ()

            try:
                latest_stage2_results = tuple(
                    result
                )
            except TypeError:
                latest_stage2_results = ()

            return result

        coordinator = ScanCoordinator(
            stage1_runner=(
                self._stage1_runner
            ),
            stage2_runner=(
                stage2_runner_wrapper
            ),
            stage1_interval_seconds=(
                self._stage1_interval_seconds
            ),
            stage2_max_concurrent_checks=(
                self._stage2_max_concurrent_checks
            ),
            stage2_priority=(
                self._stage2_priority
            ),
        )

        async def cycle_handler():
            coordinator_result = (
                await coordinator.run_cycle()
            )

            profitable_results = ()

            if latest_stage2_results:
                profitable_results = (
                    await pipeline.process_many(
                        latest_stage2_results
                    )
                )

            return coordinator_result

        runner = ApplicationRunner(
            coordinator=coordinator,
            cycle_handler=cycle_handler,
            reliability=self._reliability,
        )

        return ApplicationContext(
            scanner_engine=self._scanner_engine,
            aggregator_engine=(
                self._aggregator_engine
            ),
            coordinator=coordinator,
            pipeline=pipeline,
            runner=runner,
        )

    def create(
        self,
    ) -> ApplicationContext:
        """
        Compatibility alias.
        """

        return self.build()
