"""
Stage runtime adapter.

Responsibility:
    Execute the existing Stage 1 and Stage 2 engines.

Compatibility:
    New interfaces are preferred.
    Legacy run_* interfaces are supported automatically.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal


class StageRuntime:
    """
    Adapter around existing scanner engines.
    """

    def __init__(
        self,
        *,
        scanner_engine,
        stage2_engine,
    ) -> None:
        if scanner_engine is None:
            raise ValueError(
                "scanner_engine cannot be None."
            )

        if stage2_engine is None:
            raise ValueError(
                "stage2_engine cannot be None."
            )

        self._scanner_engine = scanner_engine
        self._stage2_engine = stage2_engine

    async def run_stage1(
        self,
        *,
        chain_id: int,
        amount_usdt: Decimal,
        max_tokens: int | None = None,
    ):
        """
        Run Stage 1 using the current interface first.
        """

        method = getattr(
            self._scanner_engine,
            "scan_stage1",
            None,
        )

        if callable(method):
            return await method(
                chain_id=chain_id,
                amount_usdt=amount_usdt,
                max_tokens=max_tokens,
            )

        legacy = getattr(
            self._scanner_engine,
            "run_stage1",
            None,
        )

        if callable(legacy):
            return await legacy(
                chain_id=chain_id,
                amount_usdt=amount_usdt,
                max_tokens=max_tokens,
            )

        raise AttributeError(
            "ScannerEngine must provide either "
            "scan_stage1() or run_stage1()."
        )

    async def run_stage2(
        self,
        stage1_results: Iterable,
    ):
        """
        Run Stage 2 using the current interface first.
        """

        method = getattr(
            self._stage2_engine,
            "scan_stage2",
            None,
        )

        if callable(method):
            return await method(
                stage1_results
            )

        legacy = getattr(
            self._stage2_engine,
            "run_stage2",
            None,
        )

        if callable(legacy):
            return await legacy(
                stage1_results
            )

        fallback = getattr(
            self._stage2_engine,
            "run",
            None,
        )

        if callable(fallback):
            return await fallback(
                stage1_results
            )

        raise AttributeError(
            "Stage2Engine must provide "
            "scan_stage2(), run_stage2() or run()."
        )

    async def stage1(
        self,
        *,
        chain_id: int,
        amount_usdt: Decimal,
        max_tokens: int | None = None,
    ):
        """
        Compatibility alias for run_stage1().
        """

        return await self.run_stage1(
            chain_id=chain_id,
            amount_usdt=amount_usdt,
            max_tokens=max_tokens,
        )

    async def stage2(
        self,
        stage1_results: Iterable,
    ):
        """
        Compatibility alias for run_stage2().
        """

        return await self.run_stage2(
            stage1_results
        )
