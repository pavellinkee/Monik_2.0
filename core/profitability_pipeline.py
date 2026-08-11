"""
Profitability pipeline.

Responsibility:
    Connect the existing Stage 3 arbitrage engine, gas calculator
    and net-profit engine.

The existing business engines remain unchanged.

Flow:

    Stage2ScanResult
        ↓
    ArbitrageEngine
        ↓
    ArbitrageOpportunity
        ↓
    GasCalculator
        ↓
    GasCost
        ↓
    NetProfitEngine
        ↓
    NetProfitResult

This module does NOT:
    - request aggregator quotes;
    - perform Stage 1;
    - perform Stage 2;
    - access SQL;
    - send Telegram messages.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from core.arbitrage_engine import ArbitrageEngine
from core.gas_calculator import GasCalculator
from core.net_profit_engine import NetProfitEngine
from models.net_profit import NetProfitResult
from models.stage2_scan import Stage2ScanResult


class ProfitabilityPipeline:
    """
    Adapter connecting the existing profitability engines.
    """

    def __init__(
        self,
        *,
        arbitrage_engine: ArbitrageEngine,
        gas_calculator: GasCalculator,
        net_profit_engine: NetProfitEngine,
        native_token_price_provider,
        gas_price_provider=None,
    ) -> None:
        if not isinstance(
            arbitrage_engine,
            ArbitrageEngine,
        ):
            raise TypeError(
                "arbitrage_engine must be an ArbitrageEngine."
            )

        if not isinstance(
            gas_calculator,
            GasCalculator,
        ):
            raise TypeError(
                "gas_calculator must be a GasCalculator."
            )

        if not isinstance(
            net_profit_engine,
            NetProfitEngine,
        ):
            raise TypeError(
                "net_profit_engine must be a NetProfitEngine."
            )

        if not callable(
            native_token_price_provider
        ):
            raise TypeError(
                "native_token_price_provider "
                "must be callable."
            )

        if (
            gas_price_provider is not None
            and not callable(gas_price_provider)
        ):
            raise TypeError(
                "gas_price_provider must be callable."
            )

        self._arbitrage_engine = (
            arbitrage_engine
        )

        self._gas_calculator = (
            gas_calculator
        )

        self._net_profit_engine = (
            net_profit_engine
        )

        self._native_token_price_provider = (
            native_token_price_provider
        )

        self._gas_price_provider = (
            gas_price_provider
        )

    async def process(
        self,
        stage2_results: Iterable[Stage2ScanResult],
    ) -> tuple[NetProfitResult, ...]:
        """
        Convert Stage 2 results into final NetProfitResult objects.
        """

        results = tuple(stage2_results)

        for result in results:
            if not isinstance(
                result,
                Stage2ScanResult,
            ):
                raise TypeError(
                    "stage2_results must contain only "
                    "Stage2ScanResult objects."
                )

        if not results:
            return ()

        opportunities = (
            await self._arbitrage_engine.analyze_stage2(
                results
            )
        )

        final_results: list[
            NetProfitResult
        ] = []

        for opportunity in opportunities:
            native_price = (
                await self._resolve_native_price(
                    opportunity.chain_id
                )
            )

            gas_price = (
                await self._resolve_gas_price(
                    opportunity.chain_id
                )
            )

            gas_cost = (
                self._gas_calculator.calculate_opportunity(
                    opportunity=opportunity,
                    native_token_price_usdt=native_price,
                    gas_price_native=gas_price,
                )
            )

            net_result = (
                self._net_profit_engine.calculate_opportunity(
                    opportunity=opportunity,
                    gas_cost=gas_cost,
                )
            )

            final_results.append(
                net_result
            )

        return tuple(final_results)

    async def run(
        self,
        stage2_results: Iterable[Stage2ScanResult],
    ) -> tuple[NetProfitResult, ...]:
        """
        Legacy compatibility alias.
        """
        return await self.process(
            stage2_results
        )

    async def _resolve_native_price(
        self,
        chain_id: int,
    ) -> Decimal:
        """
        Resolve native-token price in USDT.
        """

        value = (
            self._native_token_price_provider(
                chain_id
            )
        )

        if hasattr(
            value,
            "__await__",
        ):
            value = await value

        price = Decimal(
            str(value)
        )

        if price <= 0:
            raise ValueError(
                "Native-token price must be greater "
                "than zero."
            )

        return price

    async def _resolve_gas_price(
        self,
        chain_id: int,
    ) -> Decimal | None:
        """
        Resolve optional gas price.

        None is allowed because GasCalculator can use
        Quote.gas_cost_native directly.
        """

        if self._gas_price_provider is None:
            return None

        value = self._gas_price_provider(
            chain_id
        )

        if hasattr(
            value,
            "__await__",
        ):
            value = await value

        if value is None:
            return None

        gas_price = Decimal(
            str(value)
        )

        if gas_price < 0:
            raise ValueError(
                "Gas price cannot be negative."
            )

        return gas_price
