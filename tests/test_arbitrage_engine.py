from decimal import Decimal

import pytest

from aggregators.quote import Quote
from core.arbitrage_engine import ArbitrageEngine
from models.stage2_scan import Stage2ScanResult


def make_stage2_result(
    amount_in: int = 1_000_000,
    amount_out_stage1: int = 1_050_000,
    amount_out_stage2: int = 1_100_000,
) -> Stage2ScanResult:

    stage1_quote = Quote(
        aggregator="1inch",
        chain_id=1,
        token_in="USDT",
        token_out="AAVE",
        amount_in=amount_in,
        amount_out=amount_out_stage1,
        gas_estimate=None,
        gas_cost_native=None,
        price_impact=None,
        route=None,
        timestamp="2026-01-01T00:00:00",
    )

    stage2_quote = Quote(
        aggregator="0x",
        chain_id=1,
        token_in="AAVE",
        token_out="USDT",
        amount_in=amount_out_stage1,
        amount_out=amount_out_stage2,
        gas_estimate=None,
        gas_cost_native=None,
        price_impact=None,
        route=None,
        timestamp="2026-01-01T00:00:01",
    )

    return Stage2ScanResult(
        chain_id=1,
        base_symbol="USDT",
        target_symbol="AAVE",
        amount_usdt=Decimal("1000"),
        buy_aggregator="1inch",
        sell_aggregator="0x",
        stage1_quote=stage1_quote,
        stage2_quote=stage2_quote,
    )


@pytest.mark.asyncio
async def test_analyze_stage2_calculates_gross_profit():
    engine = ArbitrageEngine()

    result = await engine.analyze_stage2(
        [make_stage2_result()]
    )

    assert len(result) == 1

    opportunity = result[0]

    assert opportunity.final_amount_base_units == 1_100_000
    assert opportunity.gross_profit_base_units == 100_000

    assert opportunity.gross_profit_percent == Decimal("10")

    assert opportunity.gross_profit_usdt == Decimal("100")

    assert opportunity.is_gross_profitable is True


@pytest.mark.asyncio
async def test_analyze_stage2_handles_loss():
    engine = ArbitrageEngine()

    stage2_result = make_stage2_result(
        amount_out_stage2=950_000
    )

    result = await engine.analyze_stage2(
        [stage2_result]
    )

    opportunity = result[0]

    assert opportunity.gross_profit_base_units == -50_000
    assert opportunity.gross_profit_percent == Decimal("-5")
    assert opportunity.gross_profit_usdt == Decimal("-50")
    assert opportunity.is_gross_profitable is False


@pytest.mark.asyncio
async def test_analyze_stage2_empty_input_returns_empty_tuple():
    engine = ArbitrageEngine()

    result = await engine.analyze_stage2([])

    assert result == ()


@pytest.mark.asyncio
async def test_run_stage3_is_compatible_alias():
    engine = ArbitrageEngine()

    result = await engine.run_stage3(
        [make_stage2_result()]
    )

    assert len(result) == 1
    assert result[0].gross_profit_percent == Decimal("10")


@pytest.mark.asyncio
async def test_run_is_compatible_alias():
    engine = ArbitrageEngine()

    result = await engine.run(
        [make_stage2_result()]
    )

    assert len(result) == 1
    assert result[0].gross_profit_percent == Decimal("10")


@pytest.mark.asyncio
async def test_invalid_stage2_result_is_rejected():
    engine = ArbitrageEngine()

    with pytest.raises(TypeError):
        await engine.analyze_stage2(
            [object()]
        )
