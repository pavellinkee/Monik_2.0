"""
Multi-chain and multi-amount scan planner.

Responsibility:
    Convert configured scan targets and amounts into concrete
    scan tasks.

Does NOT:
    - access aggregators;
    - make HTTP requests;
    - implement rate limiting;
    - perform caching;
    - execute scans;
    - calculate profitability.

The planner is deterministic.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from models.scan_plan import (
    ScanAmount,
    ScanPlan,
    ScanTask,
    ScanTarget,
)


class ScanPlanner:
    """
    Creates deterministic multi-chain, multi-token and
    multi-amount scan plans.
    """

    def __init__(
        self,
        *,
        max_tasks: int | None = None,
    ) -> None:
        if (
            max_tasks is not None
            and max_tasks <= 0
        ):
            raise ValueError(
                "max_tasks must be greater than zero."
            )

        self._max_tasks = max_tasks

    def build_plan(
        self,
        targets: Iterable[ScanTarget],
        amounts: Iterable[ScanAmount],
    ) -> ScanPlan:
        """
        Build a complete scan plan.

        Every target is combined with every configured amount.

        Duplicate targets and duplicate amounts are removed
        deterministically.
        """

        target_items = tuple(targets)
        amount_items = tuple(amounts)

        for target in target_items:
            if not isinstance(
                target,
                ScanTarget,
            ):
                raise TypeError(
                    "targets must contain only "
                    "ScanTarget objects."
                )

        for amount in amount_items:
            if not isinstance(
                amount,
                ScanAmount,
            ):
                raise TypeError(
                    "amounts must contain only "
                    "ScanAmount objects."
                )

            if not amount.is_positive:
                raise ValueError(
                    "Scan amounts must be greater than zero."
                )

        unique_targets = self._unique_targets(
            target_items
        )

        unique_amounts = self._unique_amounts(
            amount_items
        )

        tasks: list[ScanTask] = []

        for target in unique_targets:
            for amount in unique_amounts:
                tasks.append(
                    ScanTask(
                        chain_id=target.chain_id,
                        base_symbol=target.base_symbol,
                        base_token=target.base_token,
                        target_symbol=target.target_symbol,
                        target_token=target.target_token,
                        amount_usdt=amount.amount_usdt,
                    )
                )

                if (
                    self._max_tasks is not None
                    and len(tasks)
                    >= self._max_tasks
                ):
                    return ScanPlan(
                        tasks=tuple(tasks)
                    )

        return ScanPlan(
            tasks=tuple(tasks)
        )

    def plan(
        self,
        targets: Iterable[ScanTarget],
        amounts: Iterable[ScanAmount],
    ) -> ScanPlan:
        """
        Legacy compatibility alias for build_plan().
        """
        return self.build_plan(
            targets=targets,
            amounts=amounts,
        )

    @staticmethod
    def _unique_targets(
        targets: tuple[ScanTarget, ...],
    ) -> tuple[ScanTarget, ...]:
        seen: set[
            tuple[int, str, str]
        ] = set()

        result: list[ScanTarget] = []

        for target in targets:
            key = target.normalized_key()

            if key in seen:
                continue

            seen.add(key)
            result.append(target)

        return tuple(result)

    @staticmethod
    def _unique_amounts(
        amounts: tuple[ScanAmount, ...],
    ) -> tuple[ScanAmount, ...]:
        seen: set[Decimal] = set()

        result: list[ScanAmount] = []

        for amount in amounts:
            if amount.amount_usdt in seen:
                continue

            seen.add(amount.amount_usdt)
            result.append(amount)

        return tuple(result)
