"""
Error knowledge models.
"""

from __future__ import annotations

from datetime import datetime

from models.base_model import BaseModel


class ErrorRecord(BaseModel):
    """
    Immutable error knowledge record.
    """

    error_key: str
    component: str
    error_type: str
    message: str

    occurrences: int = 1

    first_seen: datetime | None = None
    last_seen: datetime | None = None

    @property
    def is_repeated(self) -> bool:
        """
        Return True when the error occurred more than once.
        """

        return self.occurrences > 1
