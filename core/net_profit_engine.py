"""
Net profit calculation engine.

Responsibility:
    Calculate final arbitrage profit after gas costs.

Input:
    - ArbitrageOpportunity;
    - GasCost.

Output:
    - immutable NetProfitResult.

Does NOT:
    - request external APIs;
    - calculate gas;
    - access the database;
    - filter opportunities;
    - send notifications.

Compatibility:
    Primary:
        calculate_opportunity()

    Direct interface:
        calculate()

    Legacy compatibility alias:
        run()
"""

from __future__ import annotations

from decimal import Decimal

from models.arbitrage_opportunity import ArbitrageOpportunity
from models.gas_cost import GasCost
from models.net_profit import NetProfitResult


class NetProfitEngine:
    """
    Calculates final net arbitrage profitability.
    """

    def __init__(self) -> None:
        """Create a net profit engine."""
        pass

    def calculate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        gas_cost: GasCost,
    ) -> NetProfitResult:
        """
        Calculate final net profit.

        Formula:

            net_profit_usdt =
                gross_profit_usdt
                - gas_cost_usdt

            net_profit_percent =
                net_profit_usdt
                / amount_usdt
                * 100
        """

        if not isinstance(
            opportunity,
            ArbitrageOpportunity,
        ):
            raise TypeError(
                "opportunity must be an "
                "ArbitrageOpportunity."
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

        if opportunity.amount_usdt <= Decimal("0"):
            raise ValueError(
                "opportunity.amount_usdt must be "
                "greater than zero."
            )

        gross_profit_usdt = (
            opportunity.gross_profit_usdt
        )

        gas_cost_usdt = (
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
        Compatibility interface for calculate_opportunity().
        """

        return self.calculate_opportunity(
            opportunity=opportunity,
            gas_cost=gas_cost,
        )

    def run(
        self,
        opportunity: ArbitrageOpportunity,
        gas_cost: GasCost,
    ) -> NetProfitResult:
        """
        Legacy compatibility alias.
        """

        return self.calculate_opportunity(
            opportunity=opportunity,
            gas_cost=gas_cost,
        )
