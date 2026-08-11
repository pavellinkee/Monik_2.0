"""
API budget models.

Responsibility:
    Represent immutable API budget information.
"""

from __future__ import annotations

from models.base_model import BaseModel


class ApiBudgetStatus(BaseModel):
    """
    Immutable snapshot of one API budget.
    """

    aggregator: str

    limit: int
    used: int
    reserved: int

    @property
    def remaining(self) -> int:
        """
        Return currently available budget.
        """
        return max(
            0,
            self.limit
            - self.used
            - self.reserved,
        )

    @property
    def exhausted(self) -> bool:
        """
        Return True when no request capacity remains.
        """
        return self.remaining <= 0
