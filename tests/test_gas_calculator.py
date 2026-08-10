from decimal import Decimal

import pytest

from aggregators.quote import Quote
from core.gas_calculator import GasCalculator


def make_quote(
    *,
    chain_id: int = 1,
    aggregator: str = "1inch",
    gas_estimate: int | None = 100_000,
    gas_cost_native: Decimal | None = None,
) -> Quote:
    return Quote(
        aggregator=aggregator,
        chain_id=chain_id,
        token_in="USDT",
        token_out="AAVE",
        amount_in=1_000_000,
        amount_out=1_050_000,
        gas_estimate=gas_estimate,
        gas_cost_native=gas_cost_native,
        price_impact=None,
        route=None,
        timestamp="2026-01-01T00:00:00",
    )


def test_calculates_gas_from_quote_native_cost():
    calculator = GasCalculator()

    stage1 = make_quote(
        aggregator="1inch",
        gas_cost_native=Decimal("0.001"),
    )

    stage2 = make_quote(
        aggregator="0x",
        gas_cost_native=Decimal("0.002"),
    )

    result = calculator.calculate_quotes(
        stage1_quote=stage1,
        stage2_quote=stage2,
        native_token_price_usdt=Decimal("3000"),
    )

    assert result.stage1_gas_native == Decimal("0.001")
    assert result.stage2_gas_native == Decimal("0.002")
    assert result.total_gas_native == Decimal("0.003")
    assert result.total_gas_usdt == Decimal("9")


def test_calculates_gas_from_estimate_and_gas_price():
    calculator = GasCalculator()

    stage1 = make_quote(
        gas_estimate=100_000,
        gas_cost_native=None,
    )

    stage2 = make_quote(
        aggregator="0x",
        gas_estimate=50_000,
        gas_cost_native=None,
    )

    result = calculator.calculate_quotes(
        stage1_quote=stage1,
        stage2_quote=stage2,
        native_token_price_usdt=Decimal("2000"),
        gas_price_native=Decimal("0.00000001"),
    )

    assert result.stage1_gas_native == Decimal(
        "0.001"
    )

    assert result.stage2_gas_native == Decimal(
        "0.0005"
    )

    assert result.total_gas_native == Decimal(
        "0.0015"
    )

    assert result.total_gas_usdt == Decimal(
        "3.0"
    )


def test_calculate_is_compatibility_alias():
    calculator = GasCalculator()

    stage1 = make_quote(
        gas_cost_native=Decimal("0.001")
    )

    stage2 = make_quote(
        aggregator="0x",
        gas_cost_native=Decimal("0.001")
    )

    result = calculator.calculate(
        stage1_quote=stage1,
        stage2_quote=stage2,
        native_token_price_usdt=Decimal("1000"),
    )

    assert result.total_gas_usdt == Decimal("2")


def test_rejects_different_chains():
    calculator = GasCalculator()

    stage1 = make_quote(
        chain_id=1,
        gas_cost_native=Decimal("0.001"),
    )

    stage2 = make_quote(
        chain_id=137,
        aggregator="0x",
        gas_cost_native=Decimal("0.001"),
    )

    with pytest.raises(ValueError):
        calculator.calculate_quotes(
            stage1_quote=stage1,
            stage2_quote=stage2,
            native_token_price_usdt=Decimal("1000"),
        )


def test_rejects_zero_native_price():
    calculator = GasCalculator()

    stage1 = make_quote(
        gas_cost_native=Decimal("0.001")
    )

    stage2 = make_quote(
        aggregator="0x",
        gas_cost_native=Decimal("0.001")
    )

    with pytest.raises(ValueError):
        calculator.calculate_quotes(
            stage1_quote=stage1,
            stage2_quote=stage2,
            native_token_price_usdt=Decimal("0"),
        )


def test_rejects_missing_gas_information():
    calculator = GasCalculator()

    stage1 = make_quote(
        gas_estimate=None,
        gas_cost_native=None,
    )

    stage2 = make_quote(
        aggregator="0x",
        gas_estimate=None,
        gas_cost_native=None,
    )

    with pytest.raises(ValueError):
        calculator.calculate_quotes(
            stage1_quote=stage1,
            stage2_quote=stage2,
            native_token_price_usdt=Decimal("1000"),
        )


def test_gas_cost_model_is_zero_for_zero_cost():
    calculator = GasCalculator()

    stage1 = make_quote(
        gas_cost_native=Decimal("0")
    )

    stage2 = make_quote(
        aggregator="0x",
        gas_cost_native=Decimal("0")
    )

    result = calculator.calculate_quotes(
        stage1_quote=stage1,
        stage2_quote=stage2,
        native_token_price_usdt=Decimal("1000"),
    )

    assert result.is_zero is True
