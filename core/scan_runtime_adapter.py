"""
Scan runtime adapter.

Responsibility:
    Adapt the generic ScanTask representation to the existing
    ScannerEngine interface.

The adapter does NOT:
    - implement aggregator requests;
    - implement rate limiting;
    - implement queues;
    - perform caching.
"""

from __future__ import annotations

from models.scan_plan import ScanTask


class ScanRuntimeAdapter:
    """
    Adapter around an existing ScannerEngine.
    """

    def __init__(
        self,
        scanner_engine,
    ) -> None:
        if scanner_engine is None:
            raise ValueError(
                "scanner_engine cannot be None."
            )

        self._scanner_engine = scanner_engine

    async def execute(
        self,
        task: ScanTask,
    ):
        """
        Execute one ScanTask through ScannerEngine.

        The concrete scanner method is intentionally resolved
        through the compatibility adapter below.
        """

        if not isinstance(
            task,
            ScanTask,
        ):
            raise TypeError(
                "task must be a ScanTask."
            )

        return await self._execute_compatible(
            task
        )

    async def run(
        self,
        task: ScanTask,
    ):
        """
        Legacy compatibility alias.
        """
        return await self.execute(task)

    async def _execute_compatible(
        self,
        task: ScanTask,
    ):
        """
        Support both known scanner invocation styles.

        Preferred:
            scan()

        Legacy:
            run()
        """

        scan_method = getattr(
            self._scanner_engine,
            "scan",
            None,
        )

        if callable(scan_method):
            return await scan_method(
                chain_id=task.chain_id,
                base_token=task.base_token,
                target_token=task.target_token,
                amount_usdt=task.amount_usdt,
            )

        run_method = getattr(
            self._scanner_engine,
            "run",
            None,
        )

        if callable(run_method):
            return await run_method(
                chain_id=task.chain_id,
                base_token=task.base_token,
                target_token=task.target_token,
                amount_usdt=task.amount_usdt,
            )

        raise AttributeError(
            "ScannerEngine must provide either "
            "'scan()' or legacy 'run()'."
        )
