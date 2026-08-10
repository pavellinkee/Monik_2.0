"""
Net profit calculator.

Responsibility:
    Calculate final arbitrage profit after gas costs.

Input:
    - ArbitrageOpportunity;
    - GasCost.

Output:
    - immutable NetProfitResult.

Does NOT:
    - calculate gas;
    - access external APIs;
    - access the database;
    - filter opportunities;
    - send notifications.

Compatibility:
    Primary:
        calculate_opportunity()

    Legacy compatibility alias:
        calculate()
"""

from __future__ import annotations

from decimal import Decimal

from models.arbitrage_opportunity import ArbitrageOpportunity
from models.gas_cost import GasCost
from models.net_profit import NetProfitResult


class NetProfitCalculator:
    """
    Calculates final arbitrage profitability after gas costs.
    """

    def __init__(self) -> None:
        """Create a net profit calculator."""
        pass

    def calculate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        gas_cost: GasCost,
    ) -> NetProfitResult:
        """
        Calculate final net profit for an arbitrage opportunity.

        Formula:

            net_profit_usdt =
                gross_profit_usdt - gas_cost_usdt

            net_profit_percent =
                net_profit_usdt / amount_usdt * 100
        """
        if not isinstance(
            opportunity,
            ArbitrageOpportunity,
        ):
            raise TypeError(
                "opportunity must be an ArbitrageOpportunity."
            )

        if not isinstance(
            gas_cost,
            GasCost,
        ):
            raise TypeError(
                "gas_cost must be a GasCost."
            )

        if opportunity.chain_id != gas_cost.chain_id:
            raise ValueError(
                "Opportunity and gas cost must use "
                "the same chain."
            )

        if opportunity.amount_usdt <= 0:
            raise ValueError(
                "opportunity.amount_usdt must be greater "
                "than zero."
            )

        gross_profit_usdt = Decimal(
            opportunity.gross_profit_usdt
        )

        gas_cost_usdt = Decimal(
            gas_cost.total_gas_usdt
        )

        net_profit_usdt = (
            gross_profit_usdt
            - gas_cost_usdt
        )

        net_profit_percent = (
            net_profit_usdt
            / opportunity.amount_usdt
            * Decimal("100")
        )

        return NetProfitResult(
            opportunity=opportunity,
            gas_cost=gas_cost,
            gross_profit_usdt=gross_profit_usdt,
            gas_cost_usdt=gas_cost_usdt,
            net_profit_usdt=net_profit_usdt,
            net_profit_percent=net_profit_percent,
        )

    def calculate(
        self,
        opportunity: ArbitrageOpportunity,
        gas_cost: GasCost,
    ) -> NetProfitResult:
        """
        Legacy compatibility alias for
        calculate_opportunity().
        """
        return self.calculate_opportunity(
            opportunity=opportunity,
            gas_cost=gas_cost,
        )
