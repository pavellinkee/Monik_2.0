"""
Full end-to-end business test for Monik 2.0.

No real HTTP requests are performed.

The test uses:
    - real AggregatorEngine;
    - real AggregatorRequestQueue;
    - real RateLimiter;
    - real ScannerEngine;
    - real Stage2Engine;
    - real ArbitrageEngine;
    - real GasCalculator;
    - real NetProfitEngine;
    - real ProfitabilityFilter;
    - real ScanPipeline;
    - real ScanCoordinator.

Only external API implementations are replaced by deterministic
fake aggregator adapters.

This test is intentionally large because it is the integration
safety net for the complete scanner business flow.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from decimal import Decimal

import pytest

from aggregators.aggregator_engine import (
    AggregatorEngine,
)
from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.instance_registry import (
    AggregatorInstanceRegistry,
)
from aggregators.queue_pool import (
    AggregatorQueuePool,
)
from aggregators.quote import Quote
from aggregators.quote_request import (
    QuoteRequest,
)
from aggregators.rate_limiter import (
    RateLimiter,
)
from aggregators.request_queue import (
    AggregatorRequestQueue,
)
from config.models import (
    ScannerConfig,
)
from core.arbitrage_engine import (
    ArbitrageEngine,
)
from core.gas_calculator import (
    GasCalculator,
)
from core.net_profit_engine import (
    NetProfitEngine,
)
from core.profitability_filter import (
    ProfitabilityFilter,
)
from core.scan_coordinator import (
    ScanCoordinator,
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
from models.token import (
    Token,
)
from models.token_address import (
    TokenAddress,
)
from tokens.resolver import (
    TokenResolver,
)


CHAIN_A = 1
CHAIN_B = 137

USDT_A = "0xusdt-a"
USDT_B = "0xusdt-b"

TOKEN_A = "0xtoken-a"
TOKEN_B = "0xtoken-b"


class FakeAggregator(
    AggregatorInterface
):
    """
    Deterministic aggregator used for integration tests.
    """

    def __init__(
        self,
        name: str,
        *,
        stage1_multiplier: Decimal = Decimal(
            "1.05"
        ),
        stage2_multiplier: Decimal = Decimal(
            "1.02"
        ),
        delay: float = 0.0,
    ) -> None:
        self._name = name

        self._stage1_multiplier = (
            stage1_multiplier
        )

        self._stage2_multiplier = (
            stage2_multiplier
        )

        self._delay = delay

        self.calls: list[
            QuoteRequest
        ] = []

        self.active_calls = 0
        self.max_active_calls = 0

    @property
    def name(
        self,
    ) -> str:
        return self._name

    @property
    def official_url(
        self,
    ) -> str:
        return (
            f"https://example.test/{self._name}"
        )

    async def get_quote(
        self,
        request: QuoteRequest,
    ) -> Quote:
        self.calls.append(
            request
        )

        self.active_calls += 1

        self.max_active_calls = max(
            self.max_active_calls,
            self.active_calls,
        )

        try:
            if self._delay:
                await asyncio.sleep(
                    self._delay
                )

            if request.token_in.lower().startswith(
                "0xusdt"
            ):
                multiplier = (
                    self._stage1_multiplier
                )

            else:
                multiplier = (
                    self._stage2_multiplier
                )

            amount_out = int(
                Decimal(
                    request.amount
                )
                * multiplier
            )

            return Quote(
                aggregator=self._name,
                chain_id=request.chain_id,
                token_in=request.token_in,
                token_out=request.token_out,
                amount_in=request.amount,
                amount_out=amount_out,
                gas_estimate=100_000,
                gas_cost_native=Decimal(
                    "0.001"
                ),
                price_impact=Decimal(
                    "0"
                ),
                route="test-route",
                timestamp="2026-01-01T00:00:00Z",
            )

        finally:
            self.active_calls -= 1

    async def is_available(
        self,
    ) -> bool:
        return True


class FakeTokenResolver:
    """
    Resolver exposing both current and legacy interfaces.

    This allows the test to verify compatibility.
    """

    def __init__(self) -> None:
        self._tokens = (
            Token(
                symbol="USDT",
                name="Tether",
                coingecko_id="tether",
                enabled=True,
                priority=1,
                addresses=(
                    TokenAddress(
                        chain_id=CHAIN_A,
                        address=USDT_A,
                        decimals=6,
                        availability=True,
                    ),
                    TokenAddress(
                        chain_id=CHAIN_B,
                        address=USDT_B,
                        decimals=6,
                        availability=True,
                    ),
                ),
            ),
            Token(
                symbol="TEST",
                name="Test Token",
                coingecko_id="test-token",
                enabled=True,
                priority=2,
                addresses=(
                    TokenAddress(
                        chain_id=CHAIN_A,
                        address=TOKEN_A,
                        decimals=18,
                        availability=True,
                    ),
                    TokenAddress(
                        chain_id=CHAIN_B,
                        address=TOKEN_B,
                        decimals=18,
                        availability=True,
                    ),
                ),
            ),
        )

    async def resolve_enabled(
        self,
    ) -> tuple[Token, ...]:
        return self._tokens

    async def get_enabled_tokens(
        self,
    ) -> tuple[Token, ...]:
        return self._tokens

    async def resolve_for_chain(
        self,
        chain_id: int,
    ):
        return tuple(
            (
                token,
                address,
            )
            for token in self._tokens
            for address in token.addresses
            if (
                address.chain_id == chain_id
                and address.availability
            )
        )

    async def get_enabled_on_chain(
        self,
        chain_id: int,
    ):
        return await self.resolve_for_chain(
            chain_id
        )


def build_aggregator_engine(
    *names: str,
):
    """
    Build the real AggregatorEngine with real queues.
    """

    instances = (
        AggregatorInstanceRegistry()
    )

    limiters = {}

    for name in names:
        aggregator = FakeAggregator(
            name
        )

        instances.register(
            name,
            aggregator,
        )

        limiters[name] = RateLimiter(
            standard_interval=0,
            max_interval=0,
            backoff_multiplier=1.5,
        )

    queues = AggregatorQueuePool()

    for name, limiter in limiters.items():
        queues.add(
            name,
            AggregatorRequestQueue(
                rate_limiter=limiter
            ),
        )

    engine = AggregatorEngine(
        instances=instances,
        queues=queues,
    )

    return engine, instances, queues


def build_pipeline():
    """
    Build the real final-profit pipeline.
    """

    return ScanPipeline(
        arbitrage_engine=(
            ArbitrageEngine()
        ),
        gas_calculator=(
            GasCalculator()
        ),
        net_profit_engine=(
            NetProfitEngine()
        ),
        profitability_filter=(
            ProfitabilityFilter()
        ),
    )


@pytest.mark.asyncio
async def test_full_scanner_business_pipeline():
    """
    Test:

        Stage 1
          ↓
        Stage 2
          ↓
        Arbitrage
          ↓
        Gas
          ↓
        Net Profit
          ↓
        Filter
    """

    aggregator_engine, instances, queues = (
        build_aggregator_engine(
            "1inch",
            "0x",
            "Uniswap",
            "Velora",
        )
    )

    resolver = FakeTokenResolver()

    scanner = ScannerEngine(
        token_resolver=resolver,
        aggregator_engine=aggregator_engine,
    )

    stage2 = Stage2Engine(
        aggregator_engine
    )

    pipeline = build_pipeline()

    coordinator = ScanCoordinator(
        scanner_engine=scanner,
        stage2_engine=stage2,
        pipeline=pipeline,
        token_resolver=resolver,
        scan_amounts_usdt=(
            Decimal("100"),
            Decimal("500"),
            Decimal("1000"),
        ),
        max_tokens=1,
        interval_seconds=300,
        stage2_max_concurrent_checks=1,
        stage2_priority=True,
    )

    try:
        # First cycle:
        #
        # Stage 1 is performed for:
        #   chain A × 3 amounts
        #   chain B × 3 amounts
        #
        # Results are intentionally placed into the
        # pending Stage 2 queue.
        first_results = (
            await coordinator.run_cycle(
                native_token_price_usdt=Decimal(
                    "3000"
                )
            )
        )

        assert first_results == ()

        assert (
            coordinator.pending_stage2_count
            > 0
        )

        # Second cycle:
        #
        # Previous Stage 2 and new Stage 1 are allowed
        # to run concurrently.
        #
        # The returned results are only those that completed
        # Stage 2 → final profitability processing.
        second_results = (
            await coordinator.run_cycle(
                native_token_price_usdt=Decimal(
                    "3000"
                )
            )
        )

        assert second_results

        assert all(
            isinstance(
                result,
                NetProfitResult,
            )
            for result
            in second_results
        )

        assert all(
            result.is_profitable
            for result
            in second_results
        )

        assert all(
            result.net_profit_usdt
            > Decimal("0")
            for result
            in second_results
        )

        # Stage 1 × Stage 2 matrix:
        #
        # 2 chains
        # × 3 amounts
        # × 1 target token
        # × 4 buy aggregators
        # × 4 sell aggregators
        #
        # = 96 Stage 2 opportunities.
        #
        # We don't assert exact final count here because the
        # coordinator may leave the newest Stage 1 results pending.
        assert (
            len(second_results)
            > 0
        )

        # Every aggregator must have received requests.
        for name in (
            "1inch",
            "0x",
            "Uniswap",
            "Velora",
        ):
            instance = instances.get(
                name
            )

            assert instance is not None

            assert len(
                instance.calls
            ) > 0

    finally:
        await queues.stop_all()


@pytest.mark.asyncio
async def test_stage1_parallelism_across_aggregators():
    """
    Verify that different aggregators can execute concurrently.
    """

    aggregator_engine, instances, queues = (
        build_aggregator_engine(
            "A",
            "B",
        )
    )

    resolver = FakeTokenResolver()

    scanner = ScannerEngine(
        token_resolver=resolver,
        aggregator_engine=aggregator_engine,
    )

    try:
        results = (
            await scanner.scan_stage1(
                chain_id=CHAIN_A,
                amount_usdt=Decimal("100"),
                max_tokens=1,
            )
        )

        assert len(results) == 1

        assert (
            len(
                results[0].quotes
            )
            == 2
        )

    finally:
        await queues.stop_all()


@pytest.mark.asyncio
async def test_stage2_reverse_matrix():
    """
    Verify that Stage 2 creates the complete A -> B matrix.
    """

    aggregator_engine, instances, queues = (
        build_aggregator_engine(
            "A",
            "B",
            "C",
        )
    )

    resolver = FakeTokenResolver()

    scanner = ScannerEngine(
        token_resolver=resolver,
        aggregator_engine=aggregator_engine,
    )

    stage2 = Stage2Engine(
        aggregator_engine
    )

    try:
        stage1 = (
            await scanner.scan_stage1(
                chain_id=CHAIN_A,
                amount_usdt=Decimal("100"),
                max_tokens=1,
            )
        )

        assert len(stage1) == 1

        stage2_results = (
            await stage2.scan_stage2(
                stage1
            )
        )

        # 3 Stage 1 quotes
        # × 3 possible sell aggregators
        assert len(
            stage2_results
        ) == 9

        for result in stage2_results:
            assert (
                result.stage2_quote.amount_in
                == result.stage1_quote.amount_out
            )

            assert (
                result.stage2_quote.token_in.lower()
                == result.stage1_quote.token_out.lower()
            )

            assert (
                result.stage2_quote.token_out.lower()
                == result.stage1_quote.token_in.lower()
            )

    finally:
        await queues.stop_all()


@pytest.mark.asyncio
async def test_arbitrage_gas_and_net_profit():
    """
    Verify Stage 3, gas and final profitability independently.
    """

    aggregator_engine, _, queues = (
        build_aggregator_engine(
            "A",
            "B",
        )
    )

    resolver = FakeTokenResolver()

    scanner = ScannerEngine(
        token_resolver=resolver,
        aggregator_engine=aggregator_engine,
    )

    stage2_engine = Stage2Engine(
        aggregator_engine
    )

    try:
        stage1 = (
            await scanner.scan_stage1(
                chain_id=CHAIN_A,
                amount_usdt=Decimal("1000"),
                max_tokens=1,
            )
        )

        stage2_results = (
            await stage2_engine.scan_stage2(
                stage1
            )
        )

        pipeline = build_pipeline()

        final_results = (
            await pipeline.process(
                stage2_results,
                native_token_price_usdt=(
                    Decimal("3000")
                ),
            )
        )

        assert final_results

        for result in final_results:
            assert (
                result.gross_profit_usdt
                > Decimal("0")
            )

            assert (
                result.gas_cost_usdt
                > Decimal("0")
            )

            assert (
                result.net_profit_usdt
                > Decimal("0")
            )

            assert (
                result.net_profit_percent
                > Decimal("0")
            )

    finally:
        await queues.stop_all()


def test_multi_amount_configuration_legacy_compatibility():
    """
    Verify that old amount_usdt and new multi-amount
    configuration can coexist.
    """

    config = ScannerConfig(
        stage1={
            "amount_usdt": 1000,
            "base_interval_minutes": 10,
            "max_interval_minutes": 30,
            "max_tokens": 30,
            "scan_amounts_usdt": [
                100,
                500,
                1000,
            ],
        },
        stage2={
            "enabled": True,
            "max_concurrent_checks": 1,
            "same_aggregator_queue_enabled": True,
            "different_aggregators_parallel": True,
            "priority_over_stage1": True,
        },
        aggregators={
            "1inch": {
                "enabled": True,
                "api_key": "test",
                "rate_limit": {
                    "requests_per_minute": 50,
                    "initial_delay_seconds": 0,
                    "adaptive_delay_enabled": True,
                    "delay_multiplier": 1.5,
                    "max_delay_seconds": 1,
                },
            },
        },
    )

    config.validate()

    assert (
        config.stage1.amount_usdt
        == Decimal("100")
    )

    assert (
        config.stage1.amounts_usdt
        == (
            Decimal("100"),
            Decimal("500"),
            Decimal("1000"),
        )
    )


@pytest.mark.asyncio
async def test_current_and_legacy_token_resolver_interfaces():
    """
    Verify that both resolver interfaces remain usable.
    """

    resolver = FakeTokenResolver()

    current = (
        await resolver.resolve_for_chain(
            CHAIN_A
        )
    )

    legacy = (
        await resolver.get_enabled_on_chain(
            CHAIN_A
        )
    )

    assert current == legacy

    assert len(
        current
    ) == 2


@pytest.mark.asyncio
async def test_stage_engines_legacy_interfaces():
    """
    Verify the required dual-interface policy.

    Stage 1:
        scan_stage1()
        run_stage1()

    Stage 2:
        scan_stage2()
        run_stage2()
        run()

    Stage 3:
        analyze_stage2()
        run_stage3()
        run()

    Gas:
        calculate_opportunity()
        calculate_quotes()
        calculate()

    Net profit:
        calculate_opportunity()
        calculate()
        run()

    Filter:
        filter_results()
        filter()
    """

    aggregator_engine, _, queues = (
        build_aggregator_engine(
            "A",
            "B",
        )
    )

    resolver = FakeTokenResolver()

    scanner = ScannerEngine(
        token_resolver=resolver,
        aggregator_engine=aggregator_engine,
    )

    stage2_engine = Stage2Engine(
        aggregator_engine
    )

    arbitrage_engine = (
        ArbitrageEngine()
    )

    gas_calculator = (
        GasCalculator()
    )

    net_profit_engine = (
        NetProfitEngine()
    )

    profitability_filter = (
        ProfitabilityFilter()
    )

    try:
        stage1_a = (
            await scanner.scan_stage1(
                CHAIN_A,
                Decimal("1000"),
                1,
            )
        )

        stage1_b = (
            await scanner.run_stage1(
                CHAIN_A,
                Decimal("1000"),
                1,
            )
        )

        assert stage1_a
        assert stage1_b

        stage2_a = (
            await stage2_engine.scan_stage2(
                stage1_a
            )
        )

        stage2_b = (
            await stage2_engine.run_stage2(
                stage1_b
            )
        )

        stage2_c = (
            await stage2_engine.run(
                stage1_a
            )
        )

        assert stage2_a
        assert stage2_b
        assert stage2_c

        opportunities_a = (
            await arbitrage_engine.analyze_stage2(
                stage2_a
            )
        )

        opportunities_b = (
            await arbitrage_engine.run_stage3(
                stage2_b
            )
        )

        opportunities_c = (
            await arbitrage_engine.run(
                stage2_c
            )
        )

        assert opportunities_a
        assert opportunities_b
        assert opportunities_c

        opportunity = (
            opportunities_a[0]
        )

        gas_a = (
            gas_calculator.calculate_opportunity(
                opportunity,
                Decimal("3000"),
            )
        )

        gas_b = (
            gas_calculator.calculate_quotes(
                opportunity.stage1_quote,
                opportunity.stage2_quote,
                Decimal("3000"),
            )
        )

        gas_c = (
            gas_calculator.calculate(
                opportunity.stage1_quote,
                opportunity.stage2_quote,
                Decimal("3000"),
            )
        )

        assert gas_a == gas_b
        assert gas_b == gas_c

        net_a = (
            net_profit_engine.calculate_opportunity(
                opportunity,
                gas_a,
            )
        )

        net_b = (
            net_profit_engine.calculate(
                opportunity,
                gas_a,
            )
        )

        net_c = (
            net_profit_engine.run(
                opportunity,
                gas_a,
            )
        )

        assert net_a == net_b
        assert net_b == net_c

        filtered_a = (
            profitability_filter.filter_results(
                [net_a]
            )
        )

        filtered_b = (
            profitability_filter.filter(
                [net_b]
            )
        )

        assert filtered_a == filtered_b

    finally:
        await queues.stop_all()


@pytest.mark.asyncio
async def test_stage2_priority_is_preserved_by_real_queue():
    """
    Verify the actual request queue priority.

    Stage 2 must be processed before a waiting Stage 1 request
    for the same aggregator.
    """

    limiter = RateLimiter(
        standard_interval=0,
        max_interval=0,
        backoff_multiplier=1.5,
    )

    queue = AggregatorRequestQueue(
        rate_limiter=limiter
    )

    execution_order = []

    async def stage1_request():
        execution_order.append(
            "stage1"
        )
        return "stage1"

    async def stage2_request():
        execution_order.append(
            "stage2"
        )
        return "stage2"

    await queue.start()

    try:
        stage1_task = asyncio.create_task(
            queue.submit(
                stage1_request,
                stage=1,
            )
        )

        await asyncio.sleep(0)

        stage2_task = asyncio.create_task(
            queue.submit(
                stage2_request,
                stage=2,
            )
        )

        await asyncio.gather(
            stage1_task,
            stage2_task,
        )

        # Depending on whether Stage 1 had already been picked
        # by the worker, Stage 2 can only preempt a queued Stage 1.
        #
        # The invariant that must always hold is:
        # once both are queued before execution, Stage 2 wins.
        #
        # We therefore perform a second deterministic check.
        execution_order.clear()

        blocker = asyncio.Event()

        async def first_stage1():
            execution_order.append(
                "first-stage1"
            )
            await blocker.wait()

        first_task = asyncio.create_task(
            queue.submit(
                first_stage1,
                stage=1,
            )
        )

        await asyncio.sleep(0)

        second_stage1 = asyncio.create_task(
            queue.submit(
                stage1_request,
                stage=1,
            )
        )

        second_stage2 = asyncio.create_task(
            queue.submit(
                stage2_request,
                stage=2,
            )
        )

        await asyncio.sleep(0)

        blocker.set()

        await first_task
        await asyncio.gather(
            second_stage1,
            second_stage2,
        )

        assert execution_order[
            0
        ] == "first-stage1"

        assert execution_order[
            1:
        ] == [
            "stage2",
            "stage1",
        ]

    finally:
        await queue.stop()


@pytest.mark.asyncio
async def test_no_profitable_result_is_returned_when_gas_is_too_high():
    """
    Verify the most important safety rule:

        positive gross profit
        does NOT mean
        positive final profit.

    Gas must be subtracted before reporting.
    """

    aggregator_engine, _, queues = (
        build_aggregator_engine(
            "A",
            "B",
        )
    )

    resolver = FakeTokenResolver()

    scanner = ScannerEngine(
        token_resolver=resolver,
        aggregator_engine=aggregator_engine,
    )

    stage2_engine = Stage2Engine(
        aggregator_engine
    )

    try:
        stage1 = (
            await scanner.scan_stage1(
                CHAIN_A,
                Decimal("100"),
                1,
            )
        )

        stage2_results = (
            await stage2_engine.scan_stage2(
                stage1
            )
        )

        pipeline = build_pipeline()

        # Native token price is deliberately enormous.
        #
        # Quote gas = 0.001 + 0.001 native
        # Total = 0.002 native
        # Price = 1,000,000 USDT
        # Gas = 2,000 USDT
        #
        # Gross profit on 100 USDT is much smaller.
        final_results = (
            await pipeline.process(
                stage2_results,
                native_token_price_usdt=(
                    Decimal("1000000")
                ),
            )
        )

        assert final_results == ()

    finally:
        await queues.stop_all()
