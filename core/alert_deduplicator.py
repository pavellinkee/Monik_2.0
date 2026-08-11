"""
Alert deduplication.

Responsibility:
    Prevent repeated Telegram alerts for the same opportunity.

This module does NOT:
    - send Telegram messages;
    - calculate profitability;
    - access SQL;
    - make API requests.

The deduplication state is intentionally in-memory for now.
Persistent alert history will be handled by the SQL layer.
"""

from __future__ import annotations

from collections import OrderedDict


class AlertDeduplicator:
    """
    In-memory bounded alert deduplication store.
    """

    def __init__(
        self,
        *,
        max_entries: int = 10_000,
    ) -> None:
        if max_entries <= 0:
            raise ValueError(
                "max_entries must be greater than zero."
            )

        self._max_entries = max_entries

        self._seen: OrderedDict[
            str,
            None,
        ] = OrderedDict()

    def is_duplicate(
        self,
        alert_key: str,
    ) -> bool:
        """
        Return True when the alert key was already seen.
        """
        self._validate_key(alert_key)

        return alert_key in self._seen

    def remember(
        self,
        alert_key: str,
    ) -> None:
        """
        Remember an alert key.
        """
        self._validate_key(alert_key)

        if alert_key in self._seen:
            self._seen.move_to_end(
                alert_key
            )
            return

        self._seen[
            alert_key
        ] = None

        while len(self._seen) > self._max_entries:
            self._seen.popitem(
                last=False
            )

    def check_and_remember(
        self,
        alert_key: str,
    ) -> bool:
        """
        Check whether an alert is duplicate and remember it.

        Returns:
            True  -> duplicate
            False -> new alert
        """
        duplicate = self.is_duplicate(
            alert_key
        )

        if not duplicate:
            self.remember(
                alert_key
            )

        return duplicate

    def clear(self) -> None:
        """
        Clear all in-memory deduplication state.
        """
        self._seen.clear()

    def size(self) -> int:
        """
        Return number of remembered alert keys.
        """
        return len(self._seen)

    def contains(
        self,
        alert_key: str,
    ) -> bool:
        """
        Compatibility alias for is_duplicate().
        """
        return self.is_duplicate(
            alert_key
        )

    def _validate_key(
        self,
        alert_key: str,
    ) -> None:
        if not isinstance(
            alert_key,
            str,
        ):
            raise TypeError(
                "alert_key must be a string."
            )

        if not alert_key.strip():
            raise ValueError(
                "alert_key cannot be empty."
            )
