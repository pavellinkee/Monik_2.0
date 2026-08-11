"""
Reliability manager.

Responsibility:
    Provide one application-level interface for diagnostics,
    health tracking and bounded recovery.

The manager does not own business logic.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from core.diagnostic_reporter import (
    DiagnosticReporter,
)
from core.error_knowledge_base import (
    ErrorKnowledgeBase,
)
from core.health_monitor import HealthMonitor
from core.recovery_manager import (
    RecoveryManager,
)
from models.diagnostic_event import DiagnosticEvent
from models.error_record import ErrorRecord
from models.health_status import HealthStatus


class ReliabilityManager:
    """
    Unified reliability layer.
    """

    def __init__(
        self,
        *,
        diagnostics: DiagnosticReporter | None = None,
        errors: ErrorKnowledgeBase | None = None,
        health: HealthMonitor | None = None,
        recovery: RecoveryManager | None = None,
    ) -> None:
        self.diagnostics = (
            diagnostics
            or DiagnosticReporter()
        )

        self.errors = (
            errors
            or ErrorKnowledgeBase()
        )

        self.health = (
            health
            or HealthMonitor()
        )

        self.recovery = (
            recovery
            or RecoveryManager()
        )

    async def report_error(
        self,
        component: str,
        error: Exception,
    ) -> tuple[
        DiagnosticEvent,
        ErrorRecord,
    ]:
        """
        Record an error in both diagnostic systems.
        """

        record = self.errors.record(
            component,
            error,
        )

        event = await self.diagnostics.error(
            component,
            str(error),
            error=error,
        )

        self.health.unhealthy(
            component,
            str(error),
        )

        return event, record

    async def mark_healthy(
        self,
        component: str,
        message: str = "OK",
    ) -> HealthStatus:
        """
        Mark a component healthy.
        """

        return self.health.healthy(
            component,
            message,
        )

    async def recover_component(
        self,
        component: str,
        action: Callable[
            [],
            Awaitable[bool],
        ],
    ) -> bool:
        """
        Execute bounded recovery and update health accordingly.
        """

        success = await self.recovery.recover(
            component,
            action,
        )

        if success:
            self.health.healthy(
                component,
                "Recovered successfully.",
            )

        return success

    def is_healthy(self) -> bool:
        """
        Return overall application health.
        """

        return self.health.overall_healthy()
