from decimal import Decimal

import pytest

from aggregators.quote import Quote
from core.arbitrage_engine import ArbitrageEngine
from core.net_profit_calculator import NetProfitCalculator
from models.gas_cost import GasCost
from models.net_profit import NetProfitResult
from models.stage2_scan import Stage2ScanResult


def make_stage2_result(
    *,
    amount_in: int = 1_000_000,
    amount_out_stage1: int = 1_050_000,
    amount_out_stage2: int = 1_100_000,
    amount_usdt: Decimal = Decimal("1000"),
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
        amount_usdt=amount_usdt,
        buy_aggregator="1inch",
        sell_aggregator="0x",
        stage1_quote=stage1_quote,
        stage2_quote=stage2_quote,
    )


async def make_opportunity():
    engine = ArbitrageEngine()

    result = await engine.analyze_stage2(
        [make_stage2_result()]
    )

    return result[0]


def make_gas_cost(
    *,
    chain_id: int = 1,
    total_gas_usdt: Decimal = Decimal("9"),
) -> GasCost:
    return GasCost(
        chain_id=chain_id,
        native_token_price_usdt=Decimal("3000"),
        stage1_gas_native=Decimal("0.001"),
        stage2_gas_native=Decimal("0.002"),
        total_gas_native=Decimal("0.003"),
        total_gas_usdt=total_gas_usdt,
    )


@pytest.mark.asyncio
async def test_calculates_net_profit_after_gas():
    opportunity = await make_opportunity()

    calculator = NetProfitCalculator()

    result = calculator.calculate_opportunity(
        opportunity=opportunity,
        gas_cost=make_gas_cost(
            total_gas_usdt=Decimal("9")
        ),
    )

    assert isinstance(result, NetProfitResult)
    assert result.gross_profit_usdt == Decimal("100")
    assert result.gas_cost_usdt == Decimal("9")
    assert result.net_profit_usdt == Decimal("91")
    assert result.net_profit_percent == Decimal("9.1")
    assert result.is_profitable is True


@pytest.mark.asyncio
async def test_zero_net_profit_is_not_profitable():
    opportunity = await make_opportunity()

    calculator = NetProfitCalculator()

    result = calculator.calculate_opportunity(
        opportunity=opportunity,
        gas_cost=make_gas_cost(
            total_gas_usdt=Decimal("100")
        ),
    )

    assert result.net_profit_usdt == Decimal("0")
    assert result.net_profit_percent == Decimal("0")
    assert result.is_profitable is False


@pytest.mark.asyncio
async def test_loss_after_gas_is_not_profitable():
    opportunity = await make_opportunity()

    calculator = NetProfitCalculator()

    result = calculator.calculate_opportunity(
        opportunity=opportunity,
        gas_cost=make_gas_cost(
            total_gas_usdt=Decimal("150")
        ),
    )

    assert result.net_profit_usdt == Decimal("-50")
    assert result.net_profit_percent == Decimal("-5")
    assert result.is_profitable is False


@pytest.mark.asyncio
async def test_calculate_is_legacy_compatible():
    opportunity = await make_opportunity()

    calculator = NetProfitCalculator()

    gas_cost = make_gas_cost(
        total_gas_usdt=Decimal("9")
    )

    primary = calculator.calculate_opportunity(
        opportunity=opportunity,
        gas_cost=gas_cost,
    )

    legacy = calculator.calculate(
        opportunity=opportunity,
        gas_cost=gas_cost,
    )

    assert legacy == primary


def test_rejects_invalid_opportunity():
    calculator = NetProfitCalculator()

    with pytest.raises(TypeError):
        calculator.calculate_opportunity(
            opportunity=object(),
            gas_cost=make_gas_cost(),
        )


def test_rejects_invalid_gas_cost():
    calculator = NetProfitCalculator()

    with pytest.raises(TypeError):
        calculator.calculate_opportunity(
            opportunity=object(),
            gas_cost=object(),
        )


@pytest.mark.asyncio
async def test_rejects_different_chains():
    opportunity = await make_opportunity()

    calculator = NetProfitCalculator()

    with pytest.raises(ValueError):
        calculator.calculate_opportunity(
            opportunity=opportunity,
            gas_cost=make_gas_cost(
                chain_id=137
            ),
        )
