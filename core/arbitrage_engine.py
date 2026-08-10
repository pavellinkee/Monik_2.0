"""
Stage 3 arbitrage analysis engine.

Responsibility:
    Analyze Stage 2 round-trip results and calculate gross
    arbitrage performance.

Does NOT:
    - calculate gas costs;
    - calculate net profit;
    - access external APIs;
    - access the database;
    - send notifications;
    - schedule scans.

Compatibility:
    - analyze_stage2() is the primary interface.
    - run_stage3() is a compatibility alias.
    - run() is a legacy compatibility alias.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from models.arbitrage_opportunity import (
    ArbitrageOpportunity,
)
from models.stage2_scan import Stage2ScanResult


class ArbitrageEngine:
    """
    Converts Stage 2 round-trip results into gross
    arbitrage opportunities.
    """

    def __init__(self) -> None:
        """Create an arbitrage analysis engine."""
        pass

    async def analyze_stage2(
        self,
        stage2_results: Iterable[Stage2ScanResult],
    ) -> tuple[ArbitrageOpportunity, ...]:
        """
        Analyze Stage 2 results.

        For every Stage 2 result:

            initial amount
                ↓
            Stage 1
                ↓
            Stage 2
                ↓
            final amount

        The engine calculates:

            gross profit in base units
            gross profit in USDT
            gross profit percentage

        Gas is intentionally excluded.
        """

        results = tuple(stage2_results)

        if not results:
            return ()

        for result in results:
            if not isinstance(
                result,
                Stage2ScanResult,
            ):
                raise TypeError(
                    "stage2_results must contain only "
                    "Stage2ScanResult objects."
                )

        return tuple(
            self._analyze_result(result)
            for result in results
        )

    async def run_stage3(
        self,
        stage2_results: Iterable[Stage2ScanResult],
    ) -> tuple[ArbitrageOpportunity, ...]:
        """
        Compatibility alias for analyze_stage2().
        """
        return await self.analyze_stage2(
            stage2_results
        )

    async def run(
        self,
        stage2_results: Iterable[Stage2ScanResult],
    ) -> tuple[ArbitrageOpportunity, ...]:
        """
        Legacy compatibility alias for analyze_stage2().
        """
        return await self.analyze_stage2(
            stage2_results
        )

    @staticmethod
    def _analyze_result(
        result: Stage2ScanResult,
    ) -> ArbitrageOpportunity:
        """
        Calculate gross performance for one round trip.
        """

        initial_amount = (
            result.stage1_quote.amount_in
        )

        final_amount = (
            result.round_trip_amount_out
        )

        if initial_amount <= 0:
            raise ValueError(
                "Stage 1 amount_in must be greater than zero."
            )

        if final_amount <= 0:
            raise ValueError(
                "Stage 2 amount_out must be greater than zero."
            )

        gross_profit_base_units = (
            final_amount - initial_amount
        )

        gross_profit_percent = (
            Decimal(gross_profit_base_units)
            / Decimal(initial_amount)
            * Decimal("100")
        )

        gross_profit_usdt = (
            result.amount_usdt
            * gross_profit_percent
            / Decimal("100")
        )

        return ArbitrageOpportunity(
            chain_id=result.chain_id,
            base_symbol=result.base_symbol,
            target_symbol=result.target_symbol,
            amount_usdt=result.amount_usdt,
            buy_aggregator=result.buy_aggregator,
            sell_aggregator=result.sell_aggregator,
            stage1_quote=result.stage1_quote,
            stage2_quote=result.stage2_quote,
            final_amount_base_units=final_amount,
            gross_profit_base_units=(
                gross_profit_base_units
            ),
            gross_profit_usdt=gross_profit_usdt,
            gross_profit_percent=gross_profit_percent,
        )
