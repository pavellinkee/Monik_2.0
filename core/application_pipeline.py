"""
Application pipeline.

Responsibility:
    Coordinate the already existing scanner components into one
    business pipeline.

The pipeline does NOT:
    - implement HTTP;
    - implement aggregator queues;
    - implement rate limiting;
    - calculate quotes;
    - implement SQL;
    - implement Telegram transport.

All external responsibilities are injected.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable

from core.opportunity_persistence import (
    OpportunityPersistence,
)
from core.opportunity_validator import (
    OpportunityValidator,
)
from core.profitability_filter import (
    ProfitabilityFilter,
)
from core.telegram_alert_manager import (
    TelegramAlertManager,
)
from models.net_profit import NetProfitResult
from models.stage2_scan import Stage2ScanResult


Stage3Runner = Callable[
    [Stage2ScanResult],
    Awaitable[NetProfitResult | None],
]


class ApplicationPipeline:
    """
    Coordinates the final business-processing stages.
    """

    def __init__(
        self,
        *,
        stage3_runner: Stage3Runner,
        validator: OpportunityValidator,
        profitability_filter: ProfitabilityFilter,
        persistence: OpportunityPersistence | None = None,
        telegram: TelegramAlertManager | None = None,
    ) -> None:
        if not callable(stage3_runner):
            raise TypeError(
                "stage3_runner must be callable."
            )

        self._stage3_runner = stage3_runner
        self._validator = validator
        self._profitability_filter = (
            profitability_filter
        )
        self._persistence = persistence
        self._telegram = telegram

    async def process_stage2(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> NetProfitResult | None:
        """
        Process one Stage 2 opportunity through validation,
        profitability and final processing.
        """

        if not isinstance(
            result,
            Stage2ScanResult,
        ):
            raise TypeError(
                "result must be a Stage2ScanResult."
            )

        validations = (
            self._validator.validate_opportunity(
                result=result,
                related_results=related_results,
            )
        )

        if not all(
            validation.valid
            for validation in validations
        ):
            return None

        net_result = await self._stage3_runner(
            result
        )

        if net_result is None:
            return None

        profitable = (
            self._profitability_filter.filter_results(
                [net_result]
            )
        )

        if not profitable:
            return None

        final_result = profitable[0]

        if self._persistence is not None:
            await self._persistence.persist(
                final_result
            )

        if self._telegram is not None:
            await self._telegram.send_best(
                [final_result]
            )

        return final_result

    async def process_many(
        self,
        results: Iterable[Stage2ScanResult],
    ) -> tuple[NetProfitResult, ...]:
        """
        Process multiple Stage 2 opportunities.

        Invalid, failed and non-profitable opportunities are
        omitted from the returned collection.
        """

        items = tuple(results)

        for result in items:
            if not isinstance(
                result,
                Stage2ScanResult,
            ):
                raise TypeError(
                    "results must contain only "
                    "Stage2ScanResult objects."
                )

        output: list[
            NetProfitResult
        ] = []

        for result in items:
            final_result = await self.process_stage2(
                result=result,
                related_results=items,
            )

            if final_result is not None:
                output.append(
                    final_result
                )

        return tuple(output)

    async def process(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> NetProfitResult | None:
        """
        Legacy compatibility alias.
        """
        return await self.process_stage2(
            result=result,
            related_results=related_results,
        )
