"""
Direct full scanner cycle.

Responsibility:
    Execute one complete Stage 1 → Stage 2 → validation →
    profitability cycle when explicitly requested.

Important:
    This class is NOT the production scheduler.

Production scheduling is owned exclusively by ScanCoordinator.

This class is useful for:
    - integration tests;
    - manual single-cycle execution;
    - development;
    - deterministic direct execution.

It does not run continuously.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from core.opportunity_validator import (
    OpportunityValidator,
)
from core.profitability_filter import (
    ProfitabilityFilter,
)
from core.profitability_pipeline import (
    ProfitabilityPipeline,
)
from core.stage_runtime import (
    StageRuntime,
)
from models.net_profit import (
    NetProfitResult,
)
from models.stage2_scan import (
    Stage2ScanResult,
)


class FullScanCycle:
    """
    Direct, non-scheduled full scan.
    """

    def __init__(
        self,
        *,
        stage_runtime: StageRuntime,
        profitability_pipeline: ProfitabilityPipeline,
        validator: OpportunityValidator,
        profitability_filter: ProfitabilityFilter,
        chain_ids: Iterable[int],
        scan_amounts_usdt: Iterable[Decimal],
        max_tokens: int | None = None,
    ) -> None:
        if not isinstance(
            stage_runtime,
            StageRuntime,
        ):
            raise TypeError(
                "stage_runtime must be a StageRuntime."
            )

        if not isinstance(
            profitability_pipeline,
            ProfitabilityPipeline,
        ):
            raise TypeError(
                "profitability_pipeline must be a "
                "ProfitabilityPipeline."
            )

        if not isinstance(
            validator,
            OpportunityValidator,
        ):
            raise TypeError(
                "validator must be an "
                "OpportunityValidator."
            )

        if not isinstance(
            profitability_filter,
            ProfitabilityFilter,
        ):
            raise TypeError(
                "profitability_filter must be a "
                "ProfitabilityFilter."
            )

        self._stage_runtime = (
            stage_runtime
        )

        self._profitability_pipeline = (
            profitability_pipeline
        )

        self._validator = validator

        self._profitability_filter = (
            profitability_filter
        )

        self._chain_ids = tuple(
            int(chain_id)
            for chain_id in chain_ids
        )

        self._amounts = tuple(
            Decimal(str(amount))
            for amount
            in scan_amounts_usdt
        )

        self._max_tokens = max_tokens

        if not self._chain_ids:
            raise ValueError(
                "At least one chain must be configured."
            )

        if not self._amounts:
            raise ValueError(
                "At least one scan amount must be configured."
            )

    async def run(
        self,
    ) -> tuple[NetProfitResult, ...]:
        """
        Execute one direct scan.

        This method intentionally does not use ScanCoordinator.
        """

        stage1_results = []

        for chain_id in self._chain_ids:
            for amount in self._amounts:
                results = (
                    await self._stage_runtime.run_stage1(
                        chain_id=chain_id,
                        amount_usdt=amount,
                        max_tokens=self._max_tokens,
                    )
                )

                stage1_results.extend(
                    results
                )

        if not stage1_results:
            return ()

        stage2_results = (
            await self._stage_runtime.run_stage2(
                stage1_results
            )
        )

        if not stage2_results:
            return ()

        validated = (
            self._validate_results(
                stage2_results
            )
        )

        if not validated:
            return ()

        net_results = (
            await self._profitability_pipeline.process(
                validated
            )
        )

        return (
            self._profitability_filter.filter_results(
                net_results
            )
        )

    async def execute(
        self,
    ) -> tuple[NetProfitResult, ...]:
        """
        Compatibility alias.
        """

        return await self.run()

    async def scan(
        self,
    ) -> tuple[NetProfitResult, ...]:
        """
        Compatibility alias for direct execution.
        """

        return await self.run()

    def _validate_results(
        self,
        results: Iterable[Stage2ScanResult],
    ) -> tuple[Stage2ScanResult, ...]:
        """
        Apply the existing validation layer.
        """

        items = tuple(
            results
        )

        validated = []

        for result in items:
            validations = (
                self._validator.validate_opportunity(
                    result=result,
                    related_results=items,
                )
            )

            if all(
                validation.valid
                for validation
                in validations
            ):
                validated.append(
                    result
                )

        return tuple(
            validated
        )
