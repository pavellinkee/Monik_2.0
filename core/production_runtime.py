"""
Production runtime builder.

Responsibility:
    Construct the complete Monik business runtime from
    already initialized infrastructure components.
"""

from __future__ import annotations

from core.opportunity_persistence import (
    OpportunityPersistence,
)
from core.runtime_factory import (
    RuntimeFactory,
)
from config.runtime_config import RuntimeConfig


class ProductionRuntime:
    """
    Final production runtime composition.
    """

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        scanner_engine,
        stage2_engine,
        arbitrage_engine,
        gas_calculator,
        net_profit_engine,
        native_price_provider,
        opportunity_repository=None,
        telegram=None,
        gas_price_provider=None,
    ) -> None:
        self._config = config

        self._scanner_engine = scanner_engine
        self._stage2_engine = stage2_engine

        self._arbitrage_engine = (
            arbitrage_engine
        )

        self._gas_calculator = (
            gas_calculator
        )

        self._net_profit_engine = (
            net_profit_engine
        )

        self._native_price_provider = (
            native_price_provider
        )

        self._opportunity_repository = (
            opportunity_repository
        )

        self._telegram = telegram

        self._gas_price_provider = (
            gas_price_provider
        )

    def build(
        self,
    ):
        """
        Build the complete scan-cycle orchestrator.
        """

        persistence = None

        if (
            self._opportunity_repository
            is not None
        ):
            persistence = OpportunityPersistence(
                self._opportunity_repository
            )

        factory = RuntimeFactory(
            config=self._config,
            scanner_engine=self._scanner_engine,
            stage2_engine=self._stage2_engine,
            arbitrage_engine=self._arbitrage_engine,
            gas_calculator=self._gas_calculator,
            net_profit_engine=self._net_profit_engine,
            native_price_provider=(
                self._native_price_provider
            ),
            persistence=persistence,
            telegram=self._telegram,
            gas_price_provider=(
                self._gas_price_provider
            ),
        )

        return factory.build()

    def create(
        self,
    ):
        """
        Compatibility alias.
        """

        return self.build()
