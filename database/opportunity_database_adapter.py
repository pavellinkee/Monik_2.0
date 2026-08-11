"""
Database adapter for opportunity persistence.

Responsibility:
    Adapt the existing DatabaseInterface to the
    OpportunityRepository database contract.

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
        *parameters,
    ):
        """
        Delegate SQL execution.

        Parameters are expanded because the existing
        DatabaseInterface uses execute(query, *args).
        """

        method = getattr(
            self._database,
            "execute",
            None,
        )

        if not callable(
            method
        ):
            raise AttributeError(
                "Database must provide execute()."
            )

        result = method(
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
        Delegate single-row retrieval.
        """

        method = getattr(
            self._database,
            "fetch_one",
            None,
        )

        if not callable(
            method
        ):
            raise AttributeError(
                "Database must provide fetch_one()."
            )

        result = method(
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
        Delegate multi-row retrieval.
        """

        method = getattr(
            self._database,
            "fetch_all",
            None,
        )

        if not callable(
            method
        ):
            raise AttributeError(
                "Database must provide fetch_all()."
            )

        result = method(
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
        Delegate transaction commit.
        """

        method = getattr(
            self._database,
            "commit",
            None,
        )

        if not callable(
            method
        ):
            raise AttributeError(
                "Database must provide commit()."
            )

        result = method()

        if hasattr(
            result,
            "__await__",
        ):
            await result

    async def close(
        self,
    ) -> None:
        """
        Close the underlying database.

        Supports both:
            disconnect()
            close()
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
