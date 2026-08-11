"""
Health status models.
"""

from __future__ import annotations

from datetime import datetime

from models.base_model import BaseModel


class HealthStatus(BaseModel):
    """
    Immutable application health snapshot.
    """

    healthy: bool
    component: str
    message: str

    checked_at: datetime | None = None

    @property
    def is_healthy(self) -> bool:
        """
        Compatibility alias.
        """

        return self.healthy
