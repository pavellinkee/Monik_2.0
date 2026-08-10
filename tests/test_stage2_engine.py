from decimal import Decimal

import pytest

from aggregators.aggregator_engine import AggregatorEngine
from aggregators.instance_registry import AggregatorInstanceRegistry
from aggregators.queue_pool import AggregatorQueuePool
from aggregators.quote import Quote
from core.stage2_engine import Stage2Engine
from models.stage1_scan import Stage1ScanResult


class FakeAggregator:
    def __init__(
        self,
        aggregator_name: str,
        output_amount: int,
    ) -> None:
        self._name = aggregator_name
        self._output_amount = output_amount

    @property
    def name(self) -> str:
        return self._name

    @property
    def official_url(self) -> str:
        return f"https://{self._name}.example"

    async def get_quote(self, request):
        return Quote(
            aggregator=self._name,
            chain_id=request.chain_id,
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount,
            amount_out=self._output_amount,
            gas_estimate=None,
            gas_cost_native=None,
            price_impact=None,
            route="FAKE",
            timestamp="2026-01-01T00:00:00Z",
        )

    async def is_available(self) -> bool:
        return True


def build_engine(*aggregators):
    instances = AggregatorInstanceRegistry()
    queues = AggregatorQueuePool()

    for aggregator in aggregators:
        instances.register(
            aggregator.name,
            aggregator,
        )

        queues.register(
            aggregator.name,
        )

    return AggregatorEngine(
        instances=instances,
        queues=queues,
    )


def make_stage1_result(
    *,
    buy_aggregator: str = "1inch",
    amount_out: int = 1_100_000,
) -> Stage1ScanResult:
    stage1_quote = Quote(
        aggregator=buy_aggregator,
        chain_id=1,
        token_in="0xUSDT",
        token_out="0xTOKEN",
        amount_in=1_000_000,
        amount_out=amount_out,
        gas_estimate=None,
        gas_cost_native=None,
        price_impact=None,
        route="FAKE",
        timestamp="2026-01-01T00:00:00Z",
    )

    return Stage1ScanResult(
        chain_id=1,
        base_symbol="USDT",
        target_symbol="TOKEN",
        amount_usdt=Decimal("1"),
        amount_in_base_units=1_000_000,
        base_decimals=6,
        target_decimals=18,
        quotes=(stage1_quote,),
    )


@pytest.mark.asyncio
async def test_stage2_builds_reverse_quote():
    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_050_000,
    )

    engine = Stage2Engine(
        build_engine(aggregator)
    )

    stage1 = make_stage1_result()

    results = await engine.scan_stage2(
        [stage1]
    )

    assert len(results) == 1

    result = results[0]

    assert result.buy_aggregator == "1inch"
    assert result.sell_aggregator == "1inch"

    assert result.stage1_quote.token_in == "0xUSDT"
    assert result.stage1_quote.token_out == "0xTOKEN"

    assert result.stage2_quote.token_in == "0xTOKEN"
    assert result.stage2_quote.token_out == "0xUSDT"

    assert (
        result.stage2_quote.amount_in
        == result.stage1_quote.amount_out
    )


@pytest.mark.asyncio
async def test_stage2_creates_cross_aggregator_matrix():
    first = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_100_000,
    )

    second = FakeAggregator(
        aggregator_name="0x",
        output_amount=1_200_000,
    )

    engine = Stage2Engine(
        build_engine(first, second)
    )

    stage1_quote = Quote(
        aggregator="1inch",
        chain_id=1,
        token_in="0xUSDT",
        token_out="0xTOKEN",
        amount_in=1_000_000,
        amount_out=1_100_000,
        gas_estimate=None,
        gas_cost_native=None,
        price_impact=None,
        route="FAKE",
        timestamp="2026-01-01T00:00:00Z",
    )

    stage1 = Stage1ScanResult(
        chain_id=1,
        base_symbol="USDT",
        target_symbol="TOKEN",
        amount_usdt=Decimal("1"),
        amount_in_base_units=1_000_000,
        base_decimals=6,
        target_decimals=18,
        quotes=(stage1_quote,),
    )

    results = await engine.run_stage2(
        [stage1]
    )

    assert len(results) == 2

    sell_names = {
        result.sell_aggregator
        for result in results
    }

    assert sell_names == {
        "1inch",
        "0x",
    }

    for result in results:
        assert (
            result.stage2_quote.amount_in
            == 1_100_000
        )


@pytest.mark.asyncio
async def test_stage2_run_alias_is_compatible():
    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_050_000,
    )

    engine = Stage2Engine(
        build_engine(aggregator)
    )

    stage1 = make_stage1_result()

    results = await engine.run(
        [stage1]
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_stage2_empty_input_returns_empty_tuple():
    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_050_000,
    )

    engine = Stage2Engine(
        build_engine(aggregator)
    )

    results = await engine.scan_stage2([])

    assert results == ()


@pytest.mark.asyncio
async def test_stage2_rejects_invalid_input():
    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_050_000,
    )

    engine = Stage2Engine(
        build_engine(aggregator)
    )

    with pytest.raises(TypeError):
        await engine.scan_stage2(
            [object()]
        )


@pytest.mark.asyncio
async def test_stage2_requires_configured_aggregators():
    engine = Stage2Engine(
        build_engine()
    )

    stage1 = make_stage1_result()

    with pytest.raises(ValueError):
        await engine.scan_stage2(
            [stage1]
        )


def test_stage2_result_rejects_wrong_reverse_pair():
    from models.stage2_scan import Stage2ScanResult

    stage1_quote = Quote(
        aggregator="1inch",
        chain_id=1,
        token_in="0xUSDT",
        token_out="0xTOKEN",
        amount_in=1_000_000,
        amount_out=1_100_000,
        gas_estimate=None,
        gas_cost_native=None,
        price_impact=None,
        route="FAKE",
        timestamp="2026-01-01T00:00:00Z",
    )

    invalid_stage2_quote = Quote(
        aggregator="0x",
        chain_id=1,
        token_in="0xWRONG",
        token_out="0xUSDT",
        amount_in=1_100_000,
        amount_out=1_000_000,
        gas_estimate=None,
        gas_cost_native=None,
        price_impact=None,
        route="FAKE",
        timestamp="2026-01-01T00:00:00Z",
    )

    with pytest.raises(ValueError):
        Stage2ScanResult(
            chain_id=1,
            base_symbol="USDT",
            target_symbol="TOKEN",
            amount_usdt=Decimal("1"),
            buy_aggregator="1inch",
            sell_aggregator="0x",
            stage1_quote=stage1_quote,
            stage2_quote=invalid_stage2_quote,
        )
