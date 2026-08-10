"""
Stage 2 scanner engine.

Responsibility:
    Build reverse quote requests from Stage 1 results and obtain
    Stage 2 quotes from all configured aggregators.

Stage 2 flow:

    Stage1ScanResult
        |
        | for every Stage 1 quote
        v
    reverse QuoteRequest
        |
        v
    AggregatorEngine
        |
        v
    Stage2ScanResult

Important:
    Stage 2 does not calculate profitability.

For every Stage 1 quote produced by aggregator A, the engine
requests a reverse quote from every configured aggregator B.

This creates the matrix required for:

    A -> B

arbitrage analysis.

Compatibility:
    - scan_stage2() is the primary interface.
    - run_stage2() is a compatibility alias.
    - run() is an additional compatibility alias.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from decimal import Decimal

from aggregators.aggregator_engine import AggregatorEngine
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest
from models.stage1_scan import Stage1ScanResult
from models.stage2_scan import Stage2ScanResult


class Stage2Engine:
    """
    Coordinates Stage 2 reverse quote collection.

    The engine does not:
        - calculate arbitrage;
        - calculate profitability;
        - calculate gas;
        - validate final opportunities;
        - access the database;
        - send notifications;
        - schedule scans.
    """

    def __init__(
        self,
        aggregator_engine: AggregatorEngine,
    ) -> None:
        if not isinstance(
            aggregator_engine,
            AggregatorEngine,
        ):
            raise TypeError(
                "aggregator_engine must be an "
                "AggregatorEngine."
            )

        self._aggregator_engine = aggregator_engine

    async def scan_stage2(
        self,
        stage1_results: Iterable[Stage1ScanResult],
    ) -> tuple[Stage2ScanResult, ...]:
        """
        Run Stage 2 for Stage 1 results.

        For every Stage 1 quote:

            base -> target

        a reverse request is created:

            target -> base

        The reverse request uses exactly the amount_out from
        the Stage 1 quote.

        Every configured aggregator is queried for the reverse
        leg. Therefore, if Stage 1 has:

            1inch
            0x
            Uniswap
            Velora

        then a Stage 1 quote from 1inch is checked against:

            1inch
            0x
            Uniswap
            Velora

        and so on for every Stage 1 quote.
        """

        results = tuple(stage1_results)

        if not results:
            return ()

        for result in results:
            if not isinstance(
                result,
                Stage1ScanResult,
            ):
                raise TypeError(
                    "stage1_results must contain only "
                    "Stage1ScanResult objects."
                )

        aggregator_names = self._aggregator_engine.names()

        if not aggregator_names:
            raise ValueError(
                "No configured aggregators are available."
            )

        tasks = [
            self._scan_stage1_result(
                result=result,
                aggregator_names=aggregator_names,
            )
            for result in results
        ]

        nested_results = await asyncio.gather(*tasks)

        flattened: list[Stage2ScanResult] = []

        for result_group in nested_results:
            flattened.extend(result_group)

        return tuple(flattened)

    async def run_stage2(
        self,
        stage1_results: Iterable[Stage1ScanResult],
    ) -> tuple[Stage2ScanResult, ...]:
        """
        Compatibility alias for scan_stage2().
        """
        return await self.scan_stage2(stage1_results)

    async def run(
        self,
        stage1_results: Iterable[Stage1ScanResult],
    ) -> tuple[Stage2ScanResult, ...]:
        """
        Compatibility alias for scan_stage2().

        This keeps the engine usable by callers that use the
        shorter run() naming convention.
        """
        return await self.scan_stage2(stage1_results)

    async def _scan_stage1_result(
        self,
        result: Stage1ScanResult,
        aggregator_names: Iterable[str],
    ) -> tuple[Stage2ScanResult, ...]:
        """
        Build the complete reverse-quote matrix for one
        Stage 1 scan result.
        """

        tasks = [
            self._get_reverse_quote(
                result=result,
                stage1_quote=stage1_quote,
                sell_aggregator=sell_aggregator,
            )
            for stage1_quote in result.quotes
            for sell_aggregator in aggregator_names
        ]

        if not tasks:
            return ()

        stage2_results = await asyncio.gather(
            *tasks
        )

        return tuple(stage2_results)

    async def _get_reverse_quote(
        self,
        result: Stage1ScanResult,
        stage1_quote: Quote,
        sell_aggregator: str,
    ) -> Stage2ScanResult:
        """
        Request one reverse quote.

        Stage 1:

            token_in -> token_out

        Stage 2:

            token_out -> token_in
        """

        if not isinstance(
            stage1_quote,
            Quote,
        ):
            raise TypeError(
                "stage1_quote must be a Quote."
            )

        if not isinstance(
            sell_aggregator,
            str,
        ):
            raise TypeError(
                "sell_aggregator must be a string."
            )

        if not sell_aggregator.strip():
            raise ValueError(
                "sell_aggregator cannot be empty."
            )

        if stage1_quote.chain_id != result.chain_id:
            raise ValueError(
                "Stage 1 quote chain_id does not match "
                "Stage1ScanResult."
            )

        if stage1_quote.amount_out <= 0:
            raise ValueError(
                "Stage 1 quote amount_out must be "
                "greater than zero."
            )

        request = QuoteRequest(
            chain_id=result.chain_id,
            token_in=stage1_quote.token_out,
            token_out=stage1_quote.token_in,
            amount=stage1_quote.amount_out,
            token_in_decimals=result.target_decimals,
            token_out_decimals=result.base_decimals,
        )

        stage2_quote = await self._aggregator_engine.get_quote(
            aggregator_name=sell_aggregator,
            request=request,
            stage=2,
        )

        if not isinstance(
            stage2_quote,
            Quote,
        ):
            raise TypeError(
                f"Aggregator '{sell_aggregator}' "
                "returned an invalid Stage 2 quote."
            )

        return Stage2ScanResult(
            chain_id=result.chain_id,
            base_symbol=result.base_symbol,
            target_symbol=result.target_symbol,
            amount_usdt=result.amount_usdt,
            buy_aggregator=stage1_quote.aggregator,
            sell_aggregator=sell_aggregator,
            stage1_quote=stage1_quote,
            stage2_quote=stage2_quote,
        )
