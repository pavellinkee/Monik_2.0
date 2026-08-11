"""
Scan coordinator.

Responsibility:
    Schedule repeated Stage 1 / Stage 2 scanning.

Architecture:

    Previous Stage 1 results
            ↓
       pending Stage 2
            ↓
    ┌───────┴────────┐
    ↓                ↓
 Stage 2         Stage 1
 priority        next scan
    │                │
    └───────┬────────┘
            ↓
      new pending Stage 2

Important:

    AggregatorRequestQueue remains responsible for request-level
    Stage 2 > Stage 1 priority.

The coordinator is responsible only for scan-level scheduling.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Iterable
from decimal import Decimal

from core.chain_selector import (
    ChainSelector,
)
from core.scan_pipeline import (
    ScanPipeline,
)
from core.scanner_engine import (
    ScannerEngine,
)
from core.stage2_engine import (
    Stage2Engine,
)
from models.net_profit import (
    NetProfitResult,
)
from models.stage1_scan import (
    Stage1ScanResult,
)


class ScanCoordinator:
    """
    Coordinates recurring Stage 1 and Stage 2 scanning.
    """

    def __init__(
        self,
        *,
        scanner_engine: ScannerEngine,
        stage2_engine: Stage2Engine,
        pipeline: ScanPipeline,
        token_resolver,
        scan_amounts_usdt: Iterable[Decimal],
        chain_ids: Iterable[int] | None = None,
        max_tokens: int | None = 30,
        interval_seconds: float = 300.0,
        stage2_max_concurrent_checks: int = 1,
        stage2_priority: bool = True,
    ) -> None:
        if not isinstance(
            scanner_engine,
            ScannerEngine,
        ):
            raise TypeError(
                "scanner_engine must be "
                "a ScannerEngine."
            )

        if not isinstance(
            stage2_engine,
            Stage2Engine,
        ):
            raise TypeError(
                "stage2_engine must be "
                "a Stage2Engine."
            )

        if not isinstance(
            pipeline,
            ScanPipeline,
        ):
            raise TypeError(
                "pipeline must be a ScanPipeline."
            )

        if token_resolver is None:
            raise TypeError(
                "token_resolver is required."
            )

        amounts = tuple(
            Decimal(str(amount))
            for amount in scan_amounts_usdt
        )

        if not amounts:
            raise ValueError(
                "At least one scan amount is required."
            )

        if any(
            amount <= 0
            for amount in amounts
        ):
            raise ValueError(
                "All scan amounts must be greater than zero."
            )

        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than zero."
            )

        if (
            stage2_max_concurrent_checks
            <= 0
        ):
            raise ValueError(
                "stage2_max_concurrent_checks must "
                "be greater than zero."
            )

        self._scanner_engine = (
            scanner_engine
        )

        self._stage2_engine = (
            stage2_engine
        )

        self._pipeline = pipeline

        self._chain_selector = (
            ChainSelector(
                token_resolver
            )
        )

        self._configured_chain_ids = (
            None
            if chain_ids is None
            else tuple(
                int(chain_id)
                for chain_id in chain_ids
            )
        )

        self._scan_amounts = amounts

        self._max_tokens = max_tokens

        self._interval_seconds = (
            float(interval_seconds)
        )

        self._stage2_max_concurrent_checks = (
            int(
                stage2_max_concurrent_checks
            )
        )

        self._stage2_priority = bool(
            stage2_priority
        )

        self._pending_stage2: deque[
            Stage1ScanResult
        ] = deque()

        self._stop_event = asyncio.Event()

        self._last_cycle_started_at: float | None = None

        self._last_results: tuple[
            NetProfitResult,
            ...
        ] = ()

    @property
    def pending_stage2_count(
        self,
    ) -> int:
        """
        Return number of Stage 1 results waiting for Stage 2.
        """

        return len(
            self._pending_stage2
        )

    @property
    def last_results(
        self,
    ) -> tuple[NetProfitResult, ...]:
        """
        Return the latest profitable results.
        """

        return self._last_results

    @property
    def last_cycle_started_at(
        self,
    ) -> float | None:
        return self._last_cycle_started_at

    async def run_cycle(
        self,
        *,
        native_token_price_usdt: Decimal = Decimal(
            "1"
        ),
        gas_price_native: Decimal | None = None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Execute one scan cycle.

        If Stage 2 work is pending from the previous cycle,
        it runs concurrently with the new Stage 1 scan.

        The aggregator queues still enforce Stage 2 priority
        whenever both stages target the same aggregator.
        """

        self._last_cycle_started_at = (
            time.monotonic()
        )

        pending = tuple(
            self._pending_stage2
        )

        self._pending_stage2.clear()

        stage2_task = None

        if (
            pending
            and self._stage2_priority
        ):
            stage2_task = asyncio.create_task(
                self._process_stage2(
                    pending,
                    native_token_price_usdt=(
                        native_token_price_usdt
                    ),
                    gas_price_native=(
                        gas_price_native
                    ),
                )
            )

        stage1_task = asyncio.create_task(
            self._run_stage1()
        )

        if stage2_task is not None:
            stage1_results, stage2_results = (
                await asyncio.gather(
                    stage1_task,
                    stage2_task,
                )
            )
        else:
            stage1_results = (
                await stage1_task
            )

            if pending:
                stage2_results = (
                    await self._process_stage2(
                        pending,
                        native_token_price_usdt=(
                            native_token_price_usdt
                        ),
                        gas_price_native=(
                            gas_price_native
                        ),
                    )
                )
            else:
                stage2_results = ()

        self._pending_stage2.extend(
            stage1_results
        )

        self._last_results = (
            stage2_results
        )

        return stage2_results

    async def scan(
        self,
        *,
        native_token_price_usdt: Decimal = Decimal(
            "1"
        ),
        gas_price_native: Decimal | None = None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Compatibility alias.
        """

        return await self.run_cycle(
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=(
                gas_price_native
            ),
        )

    async def run(
        self,
        *,
        native_token_price_usdt: Decimal = Decimal(
            "1"
        ),
        gas_price_native: Decimal | None = None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Legacy compatibility alias.
        """

        return await self.run_cycle(
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=(
                gas_price_native
            ),
        )

    async def run_forever(
        self,
        *,
        native_token_price_usdt: Decimal = Decimal(
            "1"
        ),
        gas_price_native: Decimal | None = None,
    ) -> None:
        """
        Run recurring scan cycles.

        Default interval:
            5 minutes.

        The first cycle starts immediately.
        """

        while not self._stop_event.is_set():
            started = time.monotonic()

            await self.run_cycle(
                native_token_price_usdt=(
                    native_token_price_usdt
                ),
                gas_price_native=(
                    gas_price_native
                ),
            )

            elapsed = (
                time.monotonic()
                - started
            )

            delay = max(
                0.0,
                self._interval_seconds
                - elapsed,
            )

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=delay,
                )

            except asyncio.TimeoutError:
                continue

    async def start(
        self,
        *,
        native_token_price_usdt: Decimal = Decimal(
            "1"
        ),
        gas_price_native: Decimal | None = None,
    ) -> None:
        """
        Compatibility alias for run_forever().
        """

        await self.run_forever(
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=(
                gas_price_native
            ),
        )

    def stop(
        self,
    ) -> None:
        """
        Request graceful shutdown.
        """

        self._stop_event.set()

    async def shutdown(
        self,
    ) -> None:
        """
        Compatibility async shutdown.
        """

        self.stop()

    async def _run_stage1(
        self,
    ) -> tuple[Stage1ScanResult, ...]:
        """
        Run all configured chain/amount combinations in parallel.
        """

        if self._configured_chain_ids is None:
            chain_ids = (
                await self._chain_selector
                .get_chain_ids()
            )

        else:
            chain_ids = (
                self._configured_chain_ids
            )

        if not chain_ids:
            raise ValueError(
                "No available blockchain networks "
                "were discovered."
            )

        tasks = [
            self._scanner_engine.scan_stage1(
                chain_id=chain_id,
                amount_usdt=amount,
                max_tokens=self._max_tokens,
            )
            for chain_id in chain_ids
            for amount in self._scan_amounts
        ]

        nested_results = (
            await asyncio.gather(
                *tasks
            )
        )

        flattened: list[
            Stage1ScanResult
        ] = []

        for results in nested_results:
            flattened.extend(
                results
            )

        return tuple(
            flattened
        )

    async def _process_stage2(
        self,
        stage1_results: Iterable[
            Stage1ScanResult
        ],
        *,
        native_token_price_usdt: Decimal,
        gas_price_native: Decimal | None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Process pending Stage 2 work in bounded batches.

        Different aggregators can still execute concurrently because
        AggregatorEngine owns independent queues.
        """

        items = tuple(
            stage1_results
        )

        if not items:
            return ()

        semaphore = asyncio.Semaphore(
            self._stage2_max_concurrent_checks
        )

        async def process_one(
            result: Stage1ScanResult,
        ):
            async with semaphore:
                return await self._stage2_engine.scan_stage2(
                    (result,)
                )

        stage2_groups = await asyncio.gather(
            *(
                process_one(result)
                for result in items
            )
        )

        stage2_results = []

        for group in stage2_groups:
            stage2_results.extend(
                group
            )

        if not stage2_results:
            return ()

        return await self._pipeline.process(
            stage2_results,
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=(
                gas_price_native
            ),
        )
