"""
Database compatibility adapter.

Adapts DatabaseInterface without introducing a second
database contract.
"""

from __future__ import annotations


class OpportunityDatabaseAdapter:
    """
    Adapter for the existing DatabaseInterface.
    """

    def __init__(
        self,
        database,
    ) -> None:
        if database is None:
            raise ValueError(
                "database cannot be None."
            )

        self._database = database

    async def execute(
        self,
        query: str,
        *parameters,
    ):
        """
        Delegate execute() using the existing positional API.
        """

        result = self._database.execute(
            query,
            *parameters,
        )

        if hasattr(
            result,
            "__await__",
        ):
            return await result

        return result

    async def fetch_one(
        self,
        query: str,
        *parameters,
    ):
        """
        Delegate fetch_one().
        """

        result = self._database.fetch_one(
            query,
            *parameters,
        )

        if hasattr(
            result,
            "__await__",
        ):
            return await result

        return result

    async def fetch_all(
        self,
        query: str,
        *parameters,
    ):
        """
        Delegate fetch_all().
        """

        result = self._database.fetch_all(
            query,
            *parameters,
        )

        if hasattr(
            result,
            "__await__",
        ):
            return await result

        return result

    async def commit(
        self,
    ) -> None:
        """
        Delegate commit().
        """

        result = self._database.commit()

        if hasattr(
            result,
            "__await__",
        ):
            await result

    async def close(
        self,
    ) -> None:
        """
        Support both current disconnect() and legacy close().
        """

        disconnect = getattr(
            self._database,
            "disconnect",
            None,
        )

        if callable(
            disconnect
        ):
            result = disconnect()

            if hasattr(
                result,
                "__await__",
            ):
                await result

            return

        close = getattr(
            self._database,
            "close",
            None,
        )

        if callable(
            close
        ):
            result = close()

            if hasattr(
                result,
                "__await__",
            ):
                await result
