"""
Token repository.

Responsibility:
    Provides database access for tokens and token addresses.

Does NOT:
    - contain business logic;
    - perform API requests;
    - validate trading opportunities;
    - know about Scanner or Aggregators.
"""

from typing import Any

from database.database_interface import DatabaseInterface


class TokenRepository:
    """Repository for tokens and token addresses."""

    def __init__(self, database: DatabaseInterface):
        self._database = database

    async def get_all(self) -> list[Any]:
        """Return all tokens ordered by priority."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                symbol,
                name,
                coingecko_id,
                enabled,
                priority
            FROM tokens
            ORDER BY priority ASC, id ASC
            """
        )

    async def get_enabled(self) -> list[Any]:
        """Return enabled tokens ordered by priority."""
        return await self._database.fetch_all(
            """
            SELECT
                id,
                symbol,
                name,
                coingecko_id,
                enabled,
                priority
            FROM tokens
            WHERE enabled = 1
            ORDER BY priority ASC, id ASC
            """
        )

    async def get_by_symbol(self, symbol: str) -> Any:
        """Return a token by symbol."""
        return await self._database.fetch_one(
            """
            SELECT
                id,
                symbol,
                name,
                coingecko_id,
                enabled,
                priority
            FROM tokens
            WHERE symbol = ?
            """,
            symbol,
        )

    async def get_addresses(
        self,
        token_id: int,
        chain_id: int | None = None,
    ) -> list[Any]:
        """Return addresses for a token, optionally filtered by chain."""
        if chain_id is None:
            return await self._database.fetch_all(
                """
                SELECT
                    id,
                    token_id,
                    chain_id,
                    address,
                    decimals,
                    availability
                FROM token_addresses
                WHERE token_id = ?
                  AND availability = 1
                ORDER BY chain_id ASC
                """,
                token_id,
            )

        return await self._database.fetch_all(
            """
            SELECT
                id,
                token_id,
                chain_id,
                address,
                decimals,
                availability
            FROM token_addresses
            WHERE token_id = ?
              AND chain_id = ?
              AND availability = 1
            ORDER BY chain_id ASC
            """,
            token_id,
            chain_id,
        )

    async def get_token_with_address(
        self,
        token_id: int,
        chain_id: int,
    ) -> Any:
        """Return token and its available address for a chain."""
        return await self._database.fetch_one(
            """
            SELECT
                t.id,
                t.symbol,
                t.name,
                t.coingecko_id,
                t.enabled,
                t.priority,
                ta.id,
                ta.chain_id,
                ta.address,
                ta.decimals,
                ta.availability
            FROM tokens AS t
            INNER JOIN token_addresses AS ta
                ON ta.token_id = t.id
            WHERE t.id = ?
              AND ta.chain_id = ?
              AND t.enabled = 1
              AND ta.availability = 1
            """,
            token_id,
            chain_id,
        )
