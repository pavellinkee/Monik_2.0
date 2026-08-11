"""
Runtime scan planner.

Responsibility:
    Build ScanPlan objects from normalized RuntimeConfig and
    resolved token targets.
"""

from __future__ import annotations

from config.runtime_config import RuntimeConfig
from core.scan_planner import ScanPlanner
from models.scan_plan import (
    ScanAmount,
    ScanPlan,
    ScanTarget,
)


class RuntimeScanPlanner:
    """
    Builds production scan plans.
    """

    def __init__(
        self,
        config: RuntimeConfig,
        planner: ScanPlanner | None = None,
    ) -> None:
        if not isinstance(
            config,
            RuntimeConfig,
        ):
            raise TypeError(
                "config must be a RuntimeConfig."
            )

        self._config = config

        self._planner = (
            planner
            or ScanPlanner()
        )

    def build(
        self,
        targets: tuple[ScanTarget, ...],
    ) -> ScanPlan:
        """
        Build a plan from resolved token targets and configured
        amounts.
        """

        amounts = tuple(
            ScanAmount(
                amount_usdt=amount
            )
            for amount
            in self._config.scan_amounts_usdt
        )

        filtered_targets = tuple(
            target
            for target in targets
            if target.chain_id
            in self._config.chain_ids
        )

        return self._planner.build_plan(
            targets=filtered_targets,
            amounts=amounts,
        )

    def plan(
        self,
        targets: tuple[ScanTarget, ...],
    ) -> ScanPlan:
        """
        Legacy compatibility alias.
        """
        return self.build(targets)
