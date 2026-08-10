"""
Gas cost calculator.

Responsibility:
    Calculate the gas cost of a two-leg arbitrage operation.

Input:
    - normalized Quote objects;
    - current native-token price in USDT.

Output:
    - immutable GasCost model.

Does NOT:
    - request external gas prices;
    - access APIs;
    - access the database;
    - calculate arbitrage;
    - calculate final net profit.

Compatibility:
    Primary:
        calculate_opportunity()

    Direct quote interface:
        calculate_quotes()

    Legacy compatibility alias:
        calculate()
"""

from __future__ import annotations

from decimal import Decimal

from aggregators.quote import Quote
from models.arbitrage_opportunity import ArbitrageOpportunity
from models.gas_cost import GasCost


class GasCalculator:
    """
    Calculates normalized gas costs for arbitrage round trips.
    """

    def __init__(self) -> None:
        """Create a gas calculator."""
        pass

    def calculate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        native_token_price_usdt: Decimal,
        gas_price_native: Decimal | None = None,
    ) -> GasCost:
        """
        Calculate gas cost for an ArbitrageOpportunity.

        If Quote.gas_cost_native is available, it is used directly.

        If it is unavailable, gas_price_native may be supplied and
        gas_estimate is used as a fallback.
        """

        if not isinstance(
            opportunity,
            ArbitrageOpportunity,
        ):
            raise TypeError(
                "opportunity must be an ArbitrageOpportunity."
            )

        return self.calculate_quotes(
            stage1_quote=opportunity.stage1_quote,
            stage2_quote=opportunity.stage2_quote,
            native_token_price_usdt=native_token_price_usdt,
            gas_price_native=gas_price_native,
        )

    def calculate_quotes(
        self,
        stage1_quote: Quote,
        stage2_quote: Quote,
        native_token_price_usdt: Decimal,
        gas_price_native: Decimal | None = None,
    ) -> GasCost:
        """
        Calculate gas cost directly from two quotes.

        Both quotes must belong to the same chain.

        Gas calculation priority:

            1. Quote.gas_cost_native
            2. gas_estimate * gas_price_native

        If neither source is available, calculation fails explicitly.
        """

        if not isinstance(stage1_quote, Quote):
            raise TypeError(
                "stage1_quote must be a Quote."
            )

        if not isinstance(stage2_quote, Quote):
            raise TypeError(
                "stage2_quote must be a Quote."
            )

        native_token_price_usdt = Decimal(
            native_token_price_usdt
        )

        if native_token_price_usdt <= 0:
            raise ValueError(
                "native_token_price_usdt must be greater than zero."
            )

        if stage1_quote.chain_id != stage2_quote.chain_id:
            raise ValueError(
                "Stage 1 and Stage 2 quotes must use "
                "the same chain."
            )

        if gas_price_native is not None:
            gas_price_native = Decimal(
                gas_price_native
            )

            if gas_price_native < 0:
                raise ValueError(
                    "gas_price_native cannot be negative."
                )

        stage1_gas_native = self._resolve_gas_cost(
            quote=stage1_quote,
            gas_price_native=gas_price_native,
        )

        stage2_gas_native = self._resolve_gas_cost(
            quote=stage2_quote,
            gas_price_native=gas_price_native,
        )

        total_gas_native = (
            stage1_gas_native
            + stage2_gas_native
        )

        total_gas_usdt = (
            total_gas_native
            * native_token_price_usdt
        )

        return GasCost(
            chain_id=stage1_quote.chain_id,
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            stage1_gas_native=stage1_gas_native,
            stage2_gas_native=stage2_gas_native,
            total_gas_native=total_gas_native,
            total_gas_usdt=total_gas_usdt,
        )

    def calculate(
        self,
        stage1_quote: Quote,
        stage2_quote: Quote,
        native_token_price_usdt: Decimal,
        gas_price_native: Decimal | None = None,
    ) -> GasCost:
        """
        Legacy compatibility alias for calculate_quotes().
        """

        return self.calculate_quotes(
            stage1_quote=stage1_quote,
            stage2_quote=stage2_quote,
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=gas_price_native,
        )

    @staticmethod
    def _resolve_gas_cost(
        quote: Quote,
        gas_price_native: Decimal | None,
    ) -> Decimal:
        """
        Resolve gas cost in native-token units.
        """

        if quote.gas_cost_native is not None:
            if quote.gas_cost_native < 0:
                raise ValueError(
                    "Quote gas_cost_native cannot be negative."
                )

            return quote.gas_cost_native

        if quote.gas_estimate is None:
            raise ValueError(
                "Quote must provide either gas_cost_native "
                "or gas_estimate."
            )

        if quote.gas_estimate < 0:
            raise ValueError(
                "Quote gas_estimate cannot be negative."
            )

        if gas_price_native is None:
            raise ValueError(
                "gas_price_native is required when "
                "Quote.gas_cost_native is unavailable."
            )

        return (
            Decimal(quote.gas_estimate)
            * gas_price_native
        )
