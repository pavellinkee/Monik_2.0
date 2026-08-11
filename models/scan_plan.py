"""
Scan planning models.

Responsibility:
    Represent immutable scan-plan information.

A scan plan describes WHAT must be scanned.

It does not perform scanning and does not communicate with
aggregators.
"""

from __future__ import annotations

from decimal import Decimal

from models.base_model import BaseModel


class ScanTarget(BaseModel):
    """
    One token-pair scan target.
    """

    chain_id: int
    base_symbol: str
    base_token: str
    target_symbol: str
    target_token: str

    def normalized_key(self) -> tuple[int, str, str]:
        """
        Return a normalized identity key for this target.
        """
        return (
            self.chain_id,
            self.base_token.lower(),
            self.target_token.lower(),
        )


class ScanAmount(BaseModel):
    """
    One configured amount to scan.
    """

    amount_usdt: Decimal

    @property
    def is_positive(self) -> bool:
        """
        Return True when the amount is positive.
        """
        return self.amount_usdt > Decimal("0")


class ScanTask(BaseModel):
    """
    One concrete scan operation.

    A task combines:
        chain
        token pair
        amount
    """

    chain_id: int

    base_symbol: str
    base_token: str

    target_symbol: str
    target_token: str

    amount_usdt: Decimal

    @property
    def identity(
        self,
    ) -> tuple[int, str, str, Decimal]:
        """
        Return a stable task identity.
        """
        return (
            self.chain_id,
            self.base_token.lower(),
            self.target_token.lower(),
            self.amount_usdt,
        )


class ScanPlan(BaseModel):
    """
    Immutable collection of concrete scan tasks.
    """

    tasks: tuple[ScanTask, ...]

    @property
    def task_count(self) -> int:
        """
        Return number of planned tasks.
        """
        return len(self.tasks)

    @property
    def is_empty(self) -> bool:
        """
        Return True when no scan tasks exist.
        """
        return not self.tasks
