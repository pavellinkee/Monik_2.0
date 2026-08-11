"""
Database adapter for opportunity persistence.

Responsibility:
    Adapt the existing database implementation to the
    SqlOpportunityRepository interface.

The adapter does not create a second database abstraction.
"""

from __future__ import annotations


class OpportunityDatabaseAdapter:
    """
    Compatibility adapter around the existing database object.
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
        parameters: tuple = (),
    ):
        """
        Delegate SQL execution to the existing database.
        """

        method = getattr(
            self._database,
            "execute",
            None,
        )

        if not callable(method):
            raise AttributeError(
                "Database must provide execute()."
            )

        result = method(
            query,
            parameters,
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
        parameters: tuple = (),
    ):
        """
        Delegate single-row retrieval.
        """

        method = getattr(
            self._database,
            "fetch_one",
            None,
        )

        if callable(method):
            result = method(
                query,
                parameters,
            )

            if hasattr(
                result,
                "__await__",
            ):
                return await result

            return result

        fetch_method = getattr(
            self._database,
            "fetchrow",
            None,
        )

        if callable(fetch_method):
            result = fetch_method(
                query,
                parameters,
            )

            if hasattr(
                result,
                "__await__",
            ):
                return await result

            return result

        raise AttributeError(
            "Database must provide fetch_one() "
            "or fetchrow()."
        )

    async def close(
        self,
    ) -> None:
        """
        Close the underlying database when supported.
        """

        method = getattr(
            self._database,
            "close",
            None,
        )

        if not callable(method):
            return

        result = method()

        if hasattr(
            result,
            "__await__",
        ):
            await result
