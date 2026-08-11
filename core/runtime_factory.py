"""
Runtime factory.

Responsibility:
    Construct the scanner runtime from existing engines and
    normalized configuration.
"""

from __future__ import annotations

from decimal import Decimal

from config.runtime_config import RuntimeConfig
from core.application_pipeline import (
    ApplicationPipeline,
)
from core.coordinator_runtime import (
    CoordinatorRuntime,
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
from core.profitability_pipeline import (
    ProfitabilityPipeline,
)
from core.scan_cycle_orchestrator import (
    ScanCycleOrchestrator,
)
from core.stage_runtime import (
    StageRuntime,
)
from core.telegram_alert_manager import (
    TelegramAlertManager,
)


class RuntimeFactory:
    """
    Builds the final business runtime.
    """

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        scanner_engine,
        stage2_engine,
        arbitrage_engine,
        gas_calculator,
        net_profit_engine,
        native_price_provider,
        persistence: OpportunityPersistence | None = None,
        telegram: TelegramAlertManager | None = None,
        gas_price_provider=None,
    ) -> None:
        if not isinstance(
            config,
            RuntimeConfig,
        ):
            raise TypeError(
                "config must be a RuntimeConfig."
            )

        self._config = config
        self._scanner_engine = scanner_engine
        self._stage2_engine = stage2_engine
        self._arbitrage_engine = arbitrage_engine
        self._gas_calculator = gas_calculator
        self._net_profit_engine = net_profit_engine
        self._native_price_provider = (
            native_price_provider
        )
        self._persistence = persistence
        self._telegram = telegram
        self._gas_price_provider = (
            gas_price_provider
        )

    def build(
        self,
    ) -> ScanCycleOrchestrator:
        """
        Construct the complete business runtime.
        """

        stage_runtime = StageRuntime(
            scanner_engine=self._scanner_engine,
            stage2_engine=self._stage2_engine,
        )

        profitability_pipeline = (
            ProfitabilityPipeline(
                arbitrage_engine=self._arbitrage_engine,
                gas_calculator=self._gas_calculator,
                net_profit_engine=self._net_profit_engine,
                native_token_price_provider=(
                    self._native_price_provider.get_price
                ),
                gas_price_provider=(
                    self._gas_price_provider
                ),
            )
        )

        validator = OpportunityValidator()

        profitability_filter = (
            ProfitabilityFilter()
        )

        pipeline = ApplicationPipeline(
            stage3_runner=(
                self._make_stage3_runner(
                    profitability_pipeline
                )
            ),
            validator=validator,
            profitability_filter=(
                profitability_filter
            ),
            persistence=self._persistence,
            telegram=self._telegram,
        )

        runtime = CoordinatorRuntime(
            stage_runtime=stage_runtime,
            chain_ids=self._config.chain_ids,
            scan_amounts_usdt=(
                self._config.scan_amounts_usdt
            ),
        )

        return ScanCycleOrchestrator(
            runtime=runtime,
            pipeline=pipeline,
        )

    def create(
        self,
    ) -> ScanCycleOrchestrator:
        """
        Compatibility alias.
        """

        return self.build()

    @staticmethod
    def _make_stage3_runner(
        profitability_pipeline: ProfitabilityPipeline,
    ):
        """
        Build the Stage 3 callable expected by ApplicationPipeline.
        """

        async def runner(
            stage2_result,
        ):
            if stage2_result is None:
                return None

            results = await profitability_pipeline.process(
                [stage2_result]
            )

            if not results:
                return None

            return results[0]

        return runner
