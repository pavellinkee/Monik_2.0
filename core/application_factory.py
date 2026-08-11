"""
Application factory.

Responsibility:
    Build the production application from normalized runtime
    configuration and injected infrastructure.

This module is the composition root for the scanner.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from config.runtime_config import RuntimeConfig
from core.application_bootstrap import ApplicationBootstrap
from core.application_context import ApplicationContext
from core.application_pipeline import ApplicationPipeline
from core.application_runner import ApplicationRunner
from core.opportunity_persistence import OpportunityPersistence
from core.reliability_manager import ReliabilityManager
from core.telegram_alert_manager import TelegramAlertManager
from core.telegram_transport import TelegramTransport


class ApplicationFactory:
    """
    Builds the complete application dependency graph.
    """

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        scanner_engine,
        aggregator_engine,
        stage1_runner,
        stage2_runner,
        stage3_runner,
        persistence: OpportunityPersistence | None = None,
        telegram_transport: TelegramTransport | None = None,
        reliability: ReliabilityManager | None = None,
    ) -> None:
        if not isinstance(
            config,
            RuntimeConfig,
        ):
            raise TypeError(
                "config must be a RuntimeConfig."
            )

        self._config = config
        self._scanner_engine = scanner_engine
        self._aggregator_engine = aggregator_engine
        self._stage1_runner = stage1_runner
        self._stage2_runner = stage2_runner
        self._stage3_runner = stage3_runner
        self._persistence = persistence
        self._telegram_transport = telegram_transport
        self._reliability = reliability

    def build(
        self,
    ) -> ApplicationContext:
        """
        Build the complete application context.
        """

        telegram = None

        if (
            self._config.telegram_enabled
            and self._telegram_transport is not None
        ):
            telegram = TelegramAlertManager(
                transport=self._telegram_transport,
            )

        bootstrap = ApplicationBootstrap(
            scanner_engine=self._scanner_engine,
            aggregator_engine=self._aggregator_engine,
            stage3_runner=self._stage3_runner,
            stage1_runner=self._stage1_runner,
            stage2_runner=self._stage2_runner,
            persistence=self._persistence,
            telegram=telegram,
            reliability=self._reliability,
            stage1_interval_seconds=(
                self._config.stage1_interval_seconds
            ),
            stage2_max_concurrent_checks=(
                self._config.stage2_max_concurrent_checks
            ),
        )

        return bootstrap.build()

    def create(
        self,
    ) -> ApplicationContext:
        """
        Compatibility alias for build().
        """
        return self.build()
