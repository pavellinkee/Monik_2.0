"""
Diagnostic event models.

Responsibility:
    Represent immutable diagnostic events produced by the scanner.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models.base_model import BaseModel


class DiagnosticEvent(BaseModel):
    """
    Immutable diagnostic event.
    """

    level: str
    component: str
    message: str
    error_type: str | None = None
    timestamp: datetime | None = None

    def with_timestamp(
        self,
    ) -> "DiagnosticEvent":
        """
        Return the event with a UTC timestamp when absent.
        """

        if self.timestamp is not None:
            return self

        return self.model_copy(
            update={
                "timestamp": datetime.now(
                    timezone.utc
                )
            }
        )
