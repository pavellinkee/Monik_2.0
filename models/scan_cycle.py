"""
Scan cycle models.

Responsibility:
    Represent immutable results of a complete scanner cycle.
"""

from __future__ import annotations

from models.base_model import BaseModel


class ScanCycleResult(BaseModel):
    """
    Immutable result of one complete scan cycle.
    """

    stage1_count: int = 0
    stage2_count: int = 0
    validated_count: int = 0
    profitable_count: int = 0
    persisted_count: int = 0
    alerts_sent: int = 0

    duration_seconds: float = 0.0

    @property
    def opportunities_found(self) -> int:
        """
        Compatibility alias.
        """
        return self.profitable_count
