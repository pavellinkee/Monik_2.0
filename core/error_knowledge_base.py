"""
Error knowledge base.

Responsibility:
    Aggregate repeated errors into stable error records.

The knowledge base is deliberately independent from SQL.
Persistence can be connected later.
"""

from __future__ import annotations

from datetime import datetime, timezone

from models.error_record import ErrorRecord


class ErrorKnowledgeBase:
    """
    In-memory error knowledge base.
    """

    def __init__(self) -> None:
        self._records: dict[
            str,
            ErrorRecord,
        ] = {}

    def record(
        self,
        component: str,
        error: Exception,
    ) -> ErrorRecord:
        """
        Record one error occurrence.
        """

        if not component.strip():
            raise ValueError(
                "component cannot be empty."
            )

        if not isinstance(
            error,
            Exception,
        ):
            raise TypeError(
                "error must be an Exception."
            )

        now = datetime.now(
            timezone.utc
        )

        error_key = self.build_key(
            component,
            error,
        )

        existing = self._records.get(
            error_key
        )

        if existing is None:
            record = ErrorRecord(
                error_key=error_key,
                component=component,
                error_type=type(error).__name__,
                message=str(error),
                occurrences=1,
                first_seen=now,
                last_seen=now,
            )

            self._records[
                error_key
            ] = record

            return record

        record = existing.model_copy(
            update={
                "occurrences": (
                    existing.occurrences + 1
                ),
                "last_seen": now,
            }
        )

        self._records[
            error_key
        ] = record

        return record

    def get(
        self,
        error_key: str,
    ) -> ErrorRecord | None:
        """
        Return one known error.
        """

        return self._records.get(
            error_key
        )

    def all(
        self,
    ) -> tuple[ErrorRecord, ...]:
        """
        Return all known errors.
        """

        return tuple(
            self._records.values()
        )

    def repeated(
        self,
    ) -> tuple[ErrorRecord, ...]:
        """
        Return errors seen more than once.
        """

        return tuple(
            record
            for record in self._records.values()
            if record.is_repeated
        )

    @staticmethod
    def build_key(
        component: str,
        error: Exception,
    ) -> str:
        """
        Build a deterministic error identity.
        """

        return "|".join(
            (
                component,
                type(error).__name__,
                str(error),
            )
        )

    def clear(self) -> None:
        """
        Clear the knowledge base.
        """

        self._records.clear()

    def remember(
        self,
        component: str,
        error: Exception,
    ) -> ErrorRecord:
        """
        Compatibility alias for record().
        """

        return self.record(
            component,
            error,
        )
