"""
Recovery manager.

Responsibility:
    Execute bounded recovery actions for failed components.

The manager does NOT:
    - hide permanent failures;
    - restart the whole application;
    - perform arbitrary retries forever.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable


RecoveryAction = Callable[
    [],
    Awaitable[bool],
]


class RecoveryManager:
    """
    Coordinates bounded component recovery.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError(
                "max_attempts must be greater than zero."
            )

        self._max_attempts = max_attempts

        self._attempts: dict[
            str,
            int,
        ] = {}

    async def recover(
        self,
        component: str,
        action: RecoveryAction,
    ) -> bool:
        """
        Execute one recovery attempt.

        Returns True when recovery succeeds.
        """

        if not isinstance(
            component,
            str,
        ):
            raise TypeError(
                "component must be a string."
            )

        if not component.strip():
            raise ValueError(
                "component cannot be empty."
            )

        if not callable(action):
            raise TypeError(
                "action must be callable."
            )

        attempts = self._attempts.get(
            component,
            0,
        )

        if attempts >= self._max_attempts:
            return False

        self._attempts[
            component
        ] = attempts + 1

        try:
            success = await action()

        except Exception:
            return False

        if success:
            self._attempts.pop(
                component,
                None,
            )

        return success

    def attempts(
        self,
        component: str,
    ) -> int:
        """
        Return number of recovery attempts.
        """

        return self._attempts.get(
            component,
            0,
        )

    def reset(
        self,
        component: str,
    ) -> None:
        """
        Reset recovery state for one component.
        """

        self._attempts.pop(
            component,
            None,
        )

    def recover_component(
        self,
        component: str,
        action: RecoveryAction,
    ) -> Awaitable[bool]:
        """
        Compatibility alias for recover().
        """

        return self.recover(
            component,
            action,
        )
