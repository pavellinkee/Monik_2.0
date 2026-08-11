"""
Application bootstrap.

Responsibility:
    Construct the application dependency graph.

Important architecture rule:

    ScanCoordinator is the ONLY scheduler.

    ApplicationBootstrap:
        - creates the coordinator;
        - connects Stage 1 and Stage 2 runners;
        - processes completed Stage 2 results;
        - does not execute Stage 1/Stage 2 independently.

Stage 2 priority is therefore preserved by ScanCoordinator.
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
from core.coordinator_runtime import (
    CoordinatorRuntime,
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
from core.stage_runtime import (
    StageRuntime,
)
from core.telegram_alert_manager import (
    TelegramAlertManager,
)


class ApplicationBootstrap:
    """
    Application composition root.

    The bootstrap wires existing engines together without
    duplicating their responsibilities.
    """

    def __init__(
        self,
        *,
        scanner_engine: ScannerEngine,
        stage2_engine,
        stage3_runner,
        persistence=None,
        telegram: TelegramAlertManager | None = None,
        reliability: ReliabilityManager | None = None,
        chain_ids: tuple[int, ...] = (),
        scan_amounts_usdt: tuple = (),
        max_tokens: int | None = None,
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

        if stage2_engine is None:
            raise ValueError(
                "stage2_engine cannot be None."
            )

        if not callable(stage3_runner):
            raise TypeError(
                "stage3_runner must be callable."
            )

        if not chain_ids:
            raise ValueError(
                "At least one chain_id must be configured."
            )

        if not scan_amounts_usdt:
            raise ValueError(
                "At least one scan amount must be configured."
            )

        self._scanner_engine = scanner_engine
        self._stage2_engine = stage2_engine

        self._stage3_runner = stage3_runner

        self._persistence = persistence
        self._telegram = telegram

        self._reliability = (
            reliability
            or ReliabilityManager()
        )

        self._chain_ids = tuple(
            int(chain_id)
            for chain_id in chain_ids
        )

        self._scan_amounts_usdt = tuple(
            scan_amounts_usdt
        )

        self._max_tokens = max_tokens

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

        stage_runtime = StageRuntime(
            scanner_engine=self._scanner_engine,
            stage2_engine=self._stage2_engine,
        )

        coordinator_runtime = CoordinatorRuntime(
            stage_runtime=stage_runtime,
            chain_ids=self._chain_ids,
            scan_amounts_usdt=self._scan_amounts_usdt,
            max_tokens=self._max_tokens,
        )

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
            stage1_runner=(
                coordinator_runtime.run_stage1
            ),
            stage2_runner=(
                coordinator_runtime.run_stage2
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
            """
            Process the results produced by the coordinator.

            The coordinator itself owns scheduling.
            """

            coordinator_result = (
                await coordinator.run_cycle()
            )

            stage2_results = (
                await coordinator_runtime
                .get_last_stage2_results()
            )

            profitable_results = ()

            if stage2_results:
                profitable_results = (
                    await pipeline.process_many(
                        stage2_results
                    )
                )

            return coordinator_result, (
                profitable_results
            )

        runner = ApplicationRunner(
            coordinator=coordinator,
            cycle_handler=cycle_handler,
            reliability=self._reliability,
        )

        return ApplicationContext(
            scanner_engine=self._scanner_engine,
            aggregator_engine=(
                getattr(
                    self._scanner_engine,
                    "aggregator_engine",
                    None,
                )
            ),
            coordinator=coordinator,
            pipeline=pipeline,
            runner=runner,
        )

    def create(
        self,
    ) -> ApplicationContext:
        """
        Compatibility alias for build().
        """

        return self.build()
