"""
Application health monitor.

Responsibility:
    Track the health of scanner components.

The monitor does NOT:
    - restart services itself;
    - perform HTTP requests;
    - calculate profitability;
    - access SQL directly.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models.health_status import HealthStatus


class HealthMonitor:
    """
    In-memory application health monitor.
    """

    def __init__(self) -> None:
        self._statuses: dict[
            str,
            HealthStatus,
        ] = {}

    def healthy(
        self,
        component: str,
        message: str = "OK",
    ) -> HealthStatus:
        """
        Mark a component healthy.
        """

        return self._set_status(
            component=component,
            healthy=True,
            message=message,
        )

    def unhealthy(
        self,
        component: str,
        message: str = "UNHEALTHY",
    ) -> HealthStatus:
        """
        Mark a component unhealthy.
        """

        return self._set_status(
            component=component,
            healthy=False,
            message=message,
        )

    def get(
        self,
        component: str,
    ) -> HealthStatus | None:
        """
        Return current component status.
        """

        return self._statuses.get(
            component
        )

    def all(
        self,
    ) -> tuple[HealthStatus, ...]:
        """
        Return all component statuses.
        """

        return tuple(
            self._statuses.values()
        )

    def is_healthy(
        self,
        component: str,
    ) -> bool:
        """
        Return current health state.
        """

        status = self.get(
            component
        )

        if status is None:
            return False

        return status.healthy

    def overall_healthy(
        self,
    ) -> bool:
        """
        Return True only when every registered component is healthy.

        An empty registry is considered healthy because no component
        has reported a failure yet.
        """

        return all(
            status.healthy
            for status in self._statuses.values()
        )

    def check(
        self,
        component: str,
    ) -> HealthStatus | None:
        """
        Compatibility alias for get().
        """

        return self.get(
            component
        )

    def _set_status(
        self,
        *,
        component: str,
        healthy: bool,
        message: str,
    ) -> HealthStatus:
        if not isinstance(
            component,
            str,
        ):
            raise TypeError(
                "component must be a string."
            )

        if not component.strip():
            raise ValueError(
                "component cannot be empty."
            )

        status = HealthStatus(
            healthy=healthy,
            component=component,
            message=message,
            checked_at=datetime.now(
                timezone.utc
            ),
        )

        self._statuses[
            component
        ] = status

        return status
