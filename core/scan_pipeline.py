"""
Complete opportunity processing pipeline.

Pipeline:

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
        ↓
    ProfitabilityFilter
        ↓
    profitable opportunities

The pipeline does not:
    - schedule scans;
    - make aggregator requests;
    - access the database;
    - send Telegram messages.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from decimal import Decimal

from core.arbitrage_engine import (
    ArbitrageEngine,
)
from core.gas_calculator import (
    GasCalculator,
)
from core.net_profit_engine import (
    NetProfitEngine,
)
from core.profitability_filter import (
    ProfitabilityFilter,
)
from models.net_profit import (
    NetProfitResult,
)
from models.stage2_scan import (
    Stage2ScanResult,
)


PriceProvider = Callable[
    [object],
    Decimal | Awaitable[Decimal],
]


class ScanPipeline:
    """
    Complete Stage 2 → final-profit processing pipeline.
    """

    def __init__(
        self,
        *,
        arbitrage_engine: ArbitrageEngine,
        gas_calculator: GasCalculator,
        net_profit_engine: NetProfitEngine,
        profitability_filter: ProfitabilityFilter,
    ) -> None:
        if not isinstance(
            arbitrage_engine,
            ArbitrageEngine,
        ):
            raise TypeError(
                "arbitrage_engine must be "
                "an ArbitrageEngine."
            )

        if not isinstance(
            gas_calculator,
            GasCalculator,
        ):
            raise TypeError(
                "gas_calculator must be "
                "a GasCalculator."
            )

        if not isinstance(
            net_profit_engine,
            NetProfitEngine,
        ):
            raise TypeError(
                "net_profit_engine must be "
                "a NetProfitEngine."
            )

        if not isinstance(
            profitability_filter,
            ProfitabilityFilter,
        ):
            raise TypeError(
                "profitability_filter must be "
                "a ProfitabilityFilter."
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

        self._profitability_filter = (
            profitability_filter
        )

    async def process(
        self,
        stage2_results: Iterable[
            Stage2ScanResult
        ],
        *,
        native_token_price_usdt: (
            Decimal
            | PriceProvider
        ),
        gas_price_native: (
            Decimal
            | PriceProvider
            | None
        ) = None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Process Stage 2 results through the complete pipeline.
        """

        stage2_items = tuple(
            stage2_results
        )

        if not stage2_items:
            return ()

        for result in stage2_items:
            if not isinstance(
                result,
                Stage2ScanResult,
            ):
                raise TypeError(
                    "stage2_results must contain only "
                    "Stage2ScanResult objects."
                )

        opportunities = (
            await self._arbitrage_engine.analyze_stage2(
                stage2_items
            )
        )

        if not opportunities:
            return ()

        net_results: list[
            NetProfitResult
        ] = []

        for opportunity in opportunities:
            native_price = (
                await self._resolve_provider(
                    native_token_price_usdt,
                    opportunity,
                )
            )

            gas_price = None

            if gas_price_native is not None:
                gas_price = (
                    await self._resolve_provider(
                        gas_price_native,
                        opportunity,
                    )
                )

            gas_cost = (
                self._gas_calculator.calculate_opportunity(
                    opportunity=opportunity,
                    native_token_price_usdt=(
                        native_price
                    ),
                    gas_price_native=gas_price,
                )
            )

            net_result = (
                self._net_profit_engine.calculate_opportunity(
                    opportunity=opportunity,
                    gas_cost=gas_cost,
                )
            )

            net_results.append(
                net_result
            )

        return (
            self._profitability_filter.filter_results(
                net_results
            )
        )

    async def run(
        self,
        stage2_results: Iterable[
            Stage2ScanResult
        ],
        *,
        native_token_price_usdt: (
            Decimal
            | PriceProvider
        ),
        gas_price_native: (
            Decimal
            | PriceProvider
            | None
        ) = None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Compatibility interface.
        """

        return await self.process(
            stage2_results,
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=(
                gas_price_native
            ),
        )

    async def execute(
        self,
        stage2_results: Iterable[
            Stage2ScanResult
        ],
        *,
        native_token_price_usdt: (
            Decimal
            | PriceProvider
        ),
        gas_price_native: (
            Decimal
            | PriceProvider
            | None
        ) = None,
    ) -> tuple[NetProfitResult, ...]:
        """
        Additional compatibility alias.
        """

        return await self.process(
            stage2_results,
            native_token_price_usdt=(
                native_token_price_usdt
            ),
            gas_price_native=(
                gas_price_native
            ),
        )

    @staticmethod
    async def _resolve_provider(
        provider: Decimal | PriceProvider,
        opportunity,
    ) -> Decimal:
        """
        Resolve a constant or callable price provider.
        """

        if callable(provider):
            value = provider(
                opportunity
            )

            if inspect.isawaitable(
                value
            ):
                value = await value

        else:
            value = provider

        result = Decimal(
            str(value)
        )

        if result <= 0:
            raise ValueError(
                "Price provider must return "
                "a value greater than zero."
            )

        return result
