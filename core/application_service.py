"""
Application service.

Responsibility:
    Manage the complete application lifecycle.
"""

from __future__ import annotations

import asyncio
import signal
from types import FrameType

from core.application_context import (
    ApplicationContext,
)
from core.shutdown_manager import (
    ShutdownManager,
)


class ApplicationService:
    """
    Production application lifecycle service.
    """

    def __init__(
        self,
        context: ApplicationContext,
        *,
        shutdown_manager: ShutdownManager | None = None,
    ) -> None:
        if not isinstance(
            context,
            ApplicationContext,
        ):
            raise TypeError(
                "context must be an ApplicationContext."
            )

        self._context = context

        self._shutdown = (
            shutdown_manager
            or ShutdownManager()
        )

    async def run(
        self,
    ) -> None:
        """
        Start the application and wait for shutdown.
        """

        self._install_signal_handlers()

        runner_task = asyncio.create_task(
            self._context.runner.run_forever()
        )

        shutdown_task = asyncio.create_task(
            self._shutdown.wait()
        )

        done, pending = await asyncio.wait(
            (
                runner_task,
                shutdown_task,
            ),
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        await asyncio.gather(
            *pending,
            return_exceptions=True,
        )

        for task in done:
            if task is runner_task:
                exception = task.exception()

                if exception is not None:
                    raise exception

        await self._context.shutdown()

    def stop(
        self,
    ) -> None:
        """
        Request graceful shutdown.
        """

        self._shutdown.request_shutdown()

    def _install_signal_handlers(
        self,
    ) -> None:
        """
        Install SIGINT/SIGTERM handlers when supported.
        """

        loop = asyncio.get_running_loop()

        for sig in (
            signal.SIGINT,
            signal.SIGTERM,
        ):
            try:
                loop.add_signal_handler(
                    sig,
                    self.stop,
                )
            except (
                NotImplementedError,
                RuntimeError,
            ):
                # Some environments do not support asyncio
                # signal handlers. The application can still
                # be stopped programmatically.
                pass

    async def start(
        self,
    ) -> None:
        """
        Compatibility alias for run().
        """

        await self.run()
