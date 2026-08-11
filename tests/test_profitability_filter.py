from decimal import Decimal

import pytest

from aggregators.quote import Quote
from core.profitability_filter import ProfitabilityFilter
from models.arbitrage_opportunity import ArbitrageOpportunity
from models.gas_cost import GasCost
from models.net_profit import NetProfitResult


def make_opportunity() -> ArbitrageOpportunity:
    stage1_quote = Quote(
        aggregator="1inch",
        chain_id=1,
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

    stage2_quote = Quote(
        aggregator="0x",
        chain_id=1,
        token_in="AAVE",
        token_out="USDT",
        amount_in=1_050_000,
        amount_out=1_100_000,
        gas_estimate=None,
        gas_cost_native=Decimal("0.002"),
        price_impact=None,
        route=None,
        timestamp="2026-01-01T00:00:01",
    )

    return ArbitrageOpportunity(
        chain_id=1,
        base_symbol="USDT",
        target_symbol="AAVE",
        amount_usdt=Decimal("1000"),
        buy_aggregator="1inch",
        sell_aggregator="0x",
        stage1_quote=stage1_quote,
        stage2_quote=stage2_quote,
        final_amount_base_units=1_100_000,
        gross_profit_base_units=100_000,
        gross_profit_usdt=Decimal("100"),
        gross_profit_percent=Decimal("10"),
    )


def make_gas_cost() -> GasCost:
    return GasCost(
        chain_id=1,
        native_token_price_usdt=Decimal("3000"),
        stage1_gas_native=Decimal("0.001"),
        stage2_gas_native=Decimal("0.002"),
        total_gas_native=Decimal("0.003"),
        total_gas_usdt=Decimal("10"),
    )


def make_result(
    net_profit_usdt: str,
) -> NetProfitResult:
    return NetProfitResult(
        opportunity=make_opportunity(),
        gas_cost=make_gas_cost(),
        gross_profit_usdt=Decimal("100"),
        gas_cost_usdt=Decimal("10"),
        net_profit_usdt=Decimal(
            net_profit_usdt
        ),
        net_profit_percent=Decimal(
            net_profit_usdt
        ) / Decimal("10"),
    )


def test_keeps_only_profitable_results():
    profitable = make_result("90")
    zero = make_result("0")
    loss = make_result("-10")

    result = ProfitabilityFilter().filter_results(
        [profitable, zero, loss]
    )

    assert result == (profitable,)


def test_positive_profit_is_kept():
    result = make_result("0.01")

    filtered = ProfitabilityFilter().filter_results(
        [result]
    )

    assert filtered == (result,)


def test_zero_profit_is_removed():
    result = make_result("0")

    filtered = ProfitabilityFilter().filter_results(
        [result]
    )

    assert filtered == ()


def test_negative_profit_is_removed():
    result = make_result("-0.01")

    filtered = ProfitabilityFilter().filter_results(
        [result]
    )

    assert filtered == ()


def test_empty_input_returns_empty_tuple():
    result = ProfitabilityFilter().filter_results([])

    assert result == ()


def test_order_is_preserved():
    first = make_result("10")
    second = make_result("20")
    third = make_result("30")

    result = ProfitabilityFilter().filter_results(
        [first, second, third]
    )

    assert result == (
        first,
        second,
        third,
    )


def test_rejects_invalid_result():
    with pytest.raises(TypeError):
        ProfitabilityFilter().filter_results(
            [object()]
        )


def test_legacy_filter_interface_matches_primary():
    profitable = make_result("10")
    loss = make_result("-5")

    filter_engine = ProfitabilityFilter()

    primary = filter_engine.filter_results(
        [profitable, loss]
    )

    legacy = filter_engine.filter(
        [profitable, loss]
    )

    assert legacy == primary
