"""
Diagnostic reporter.

Responsibility:
    Provide one unified interface for reporting diagnostic
    events across the scanner.

The reporter does NOT:
    - decide how an error is recovered;
    - access external APIs;
    - send Telegram messages;
    - write SQL directly.

Storage is injected so that SQLite/PostgreSQL and test
implementations can be used without changing the reporter.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from models.diagnostic_event import DiagnosticEvent


DiagnosticSink = Callable[
    [DiagnosticEvent],
    Awaitable[None],
]


class DiagnosticReporter:
    """
    Central diagnostic event reporter.
    """

    def __init__(
        self,
        sink: DiagnosticSink | None = None,
    ) -> None:
        if sink is not None and not callable(
            sink
        ):
            raise TypeError(
                "sink must be callable."
            )

        self._sink = sink
        self._events: list[
            DiagnosticEvent
        ] = []

    async def report(
        self,
        event: DiagnosticEvent,
    ) -> DiagnosticEvent:
        """
        Report one diagnostic event.
        """

        if not isinstance(
            event,
            DiagnosticEvent,
        ):
            raise TypeError(
                "event must be a DiagnosticEvent."
            )

        event = event.with_timestamp()

        self._events.append(event)

        if self._sink is not None:
            await self._sink(event)

        return event

    async def info(
        self,
        component: str,
        message: str,
    ) -> DiagnosticEvent:
        """
        Report an informational event.
        """

        return await self.report(
            DiagnosticEvent(
                level="info",
                component=component,
                message=message,
            )
        )

    async def warning(
        self,
        component: str,
        message: str,
    ) -> DiagnosticEvent:
        """
        Report a warning.
        """

        return await self.report(
            DiagnosticEvent(
                level="warning",
                component=component,
                message=message,
            )
        )

    async def error(
        self,
        component: str,
        message: str,
        *,
        error: Exception | None = None,
    ) -> DiagnosticEvent:
        """
        Report an error.
        """

        return await self.report(
            DiagnosticEvent(
                level="error",
                component=component,
                message=message,
                error_type=(
                    type(error).__name__
                    if error is not None
                    else None
                ),
            )
        )

    async def event(
        self,
        component: str,
        message: str,
    ) -> DiagnosticEvent:
        """
        Compatibility helper for generic events.
        """

        return await self.info(
            component,
            message,
        )

    def recent(
        self,
        limit: int = 100,
    ) -> tuple[DiagnosticEvent, ...]:
        """
        Return recent in-memory diagnostic events.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        return tuple(
            self._events[-limit:]
        )

    def clear(self) -> None:
        """
        Clear the in-memory diagnostic buffer.
        """

        self._events.clear()
