from decimal import Decimal

import pytest

from aggregators.quote import Quote
from core.net_profit_engine import NetProfitEngine
from models.arbitrage_opportunity import (
    ArbitrageOpportunity,
)
from models.gas_cost import GasCost


def make_opportunity(
    *,
    amount_usdt: Decimal = Decimal("1000"),
    gross_profit_usdt: Decimal = Decimal("100"),
    chain_id: int = 1,
) -> ArbitrageOpportunity:

    stage1 = Quote(
        aggregator="1inch",
        chain_id=chain_id,
        token_in="USDT",
        token_out="AAVE",
        amount_in=1_000_000,
        amount_out=1_050_000,
        gas_estimate=None,
        gas_cost_native=Decimal("0.001"),
        price_impact=None,
        route=None,
        timestamp="2026-01-01T00:00:00",
    )

    stage2 = Quote(
        aggregator="0x",
        chain_id=chain_id,
        token_in="AAVE",
        token_out="USDT",
        amount_in=1_050_000,
        amount_out=1_100_000,
        gas_estimate=None,
        gas_cost_native=Decimal("0.001"),
        price_impact=None,
        route=None,
        timestamp="2026-01-01T00:00:01",
    )

    return ArbitrageOpportunity(
        chain_id=chain_id,
        base_symbol="USDT",
        target_symbol="AAVE",
        amount_usdt=amount_usdt,
        buy_aggregator="1inch",
        sell_aggregator="0x",
        stage1_quote=stage1,
        stage2_quote=stage2,
        final_amount_base_units=1_100_000,
        gross_profit_base_units=100_000,
        gross_profit_usdt=gross_profit_usdt,
        gross_profit_percent=Decimal("10"),
    )


def make_gas_cost(
    *,
    total_gas_usdt: Decimal = Decimal("30"),
    chain_id: int = 1,
) -> GasCost:

    return GasCost(
        chain_id=chain_id,
        native_token_price_usdt=Decimal("3000"),
        stage1_gas_native=Decimal("0.005"),
        stage2_gas_native=Decimal("0.005"),
        total_gas_native=Decimal("0.01"),
        total_gas_usdt=total_gas_usdt,
    )


def test_calculates_net_profit():
    engine = NetProfitEngine()

    opportunity = make_opportunity(
        gross_profit_usdt=Decimal("100")
    )

    gas_cost = make_gas_cost(
        total_gas_usdt=Decimal("30")
    )

    result = engine.calculate_opportunity(
        opportunity,
        gas_cost,
    )

    assert result.gross_profit_usdt == Decimal("100")
    assert result.gas_cost_usdt == Decimal("30")
    assert result.net_profit_usdt == Decimal("70")
    assert result.net_profit_percent == Decimal("7")
    assert result.is_profitable is True


def test_negative_net_profit_is_not_profitable():
    engine = NetProfitEngine()

    opportunity = make_opportunity(
        gross_profit_usdt=Decimal("20")
    )

    gas_cost = make_gas_cost(
        total_gas_usdt=Decimal("30")
    )

    result = engine.calculate_opportunity(
        opportunity,
        gas_cost,
    )

    assert result.net_profit_usdt == Decimal("-10")
    assert result.net_profit_percent == Decimal("-1")
    assert result.is_profitable is False


def test_zero_net_profit_is_not_profitable():
    engine = NetProfitEngine()

    opportunity = make_opportunity(
        gross_profit_usdt=Decimal("30")
    )

    gas_cost = make_gas_cost(
        total_gas_usdt=Decimal("30")
    )

    result = engine.calculate_opportunity(
        opportunity,
        gas_cost,
    )

    assert result.net_profit_usdt == Decimal("0")
    assert result.net_profit_percent == Decimal("0")
    assert result.is_profitable is False


def test_calculate_is_compatible_alias():
    engine = NetProfitEngine()

    opportunity = make_opportunity()
    gas_cost = make_gas_cost()

    result = engine.calculate(
        opportunity,
        gas_cost,
    )

    assert result.net_profit_usdt == Decimal("70")


def test_run_is_legacy_compatible_alias():
    engine = NetProfitEngine()

    opportunity = make_opportunity()
    gas_cost = make_gas_cost()

    result = engine.run(
        opportunity,
        gas_cost,
    )

    assert result.net_profit_usdt == Decimal("70")


def test_rejects_wrong_opportunity_type():
    engine = NetProfitEngine()

    gas_cost = make_gas_cost()

    with pytest.raises(TypeError):
        engine.calculate_opportunity(
            object(),
            gas_cost,
        )


def test_rejects_wrong_gas_cost_type():
    engine = NetProfitEngine()

    opportunity = make_opportunity()

    with pytest.raises(TypeError):
        engine.calculate_opportunity(
            opportunity,
            object(),
        )


def test_rejects_different_chains():
    engine = NetProfitEngine()

    opportunity = make_opportunity(
        chain_id=1
    )

    gas_cost = make_gas_cost(
        chain_id=137
    )

    with pytest.raises(ValueError):
        engine.calculate_opportunity(
            opportunity,
            gas_cost,
        )


def test_rejects_zero_amount():
    engine = NetProfitEngine()

    opportunity = make_opportunity(
        amount_usdt=Decimal("0")
    )

    gas_cost = make_gas_cost()

    with pytest.raises(ValueError):
        engine.calculate_opportunity(
            opportunity,
            gas_cost,
        )
