"""
Token resolver.

Responsibility:
    Converts repository/database token rows into immutable project models
    that can safely be consumed by higher-level scanner components.

Does NOT:
    - access the database directly;
    - perform API requests;
    - calculate prices;
    - calculate arbitrage;
    - calculate profit;
    - know about aggregators.

Compatibility:
    - primary interface uses resolve_* methods;
    - compatibility aliases expose get_* methods;
    - accepts both mapping-style rows and sequence/object-style rows.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from core.exceptions import TokenError
from models.token import Token
from models.token_address import TokenAddress


class TokenResolver:
    """
    Converts TokenRepository rows into Token and TokenAddress models.

    The resolver depends only on the repository contract and therefore
    remains independent from the concrete database implementation.
    """

    def __init__(self, repository: Any):
        if repository is None:
            raise TokenError(
                "Token repository is required."
            )

        self._repository = repository

    async def resolve_all(self) -> tuple[Token, ...]:
        """
        Resolve all tokens returned by the repository.

        Disabled tokens are preserved because this method represents
        the complete token catalogue.
        """

        rows = await self._repository.get_all()

        return await self._resolve_rows(
            rows,
            chain_id=None,
        )

    async def resolve_enabled(self) -> tuple[Token, ...]:
        """
        Resolve only enabled tokens.

        Tokens remain ordered exactly as returned by the repository.
        """

        rows = await self._repository.get_enabled()

        return await self._resolve_rows(
            rows,
            chain_id=None,
        )

    async def resolve_for_chain(
        self,
        chain_id: int,
    ) -> tuple[Token, ...]:
        """
        Resolve enabled tokens that have an available address
        on the requested blockchain network.
        """

        if chain_id <= 0:
            raise TokenError(
                "chain_id must be greater than 0."
            )

        rows = await self._repository.get_enabled()

        return await self._resolve_rows(
            rows,
            chain_id=chain_id,
        )

    async def resolve_by_symbol(
        self,
        symbol: str,
    ) -> Token | None:
        """
        Resolve one token by symbol.

        Returns None when the repository does not contain the token.
        """

        if not isinstance(symbol, str):
            raise TokenError(
                "symbol must be a string."
            )

        symbol = symbol.strip()

        if not symbol:
            raise TokenError(
                "symbol must not be empty."
            )

        row = await self._repository.get_by_symbol(
            symbol
        )

        if row is None:
            return None

        addresses = await self._get_addresses(
            self._row_value(row, "id", 0)
        )

        return self._build_token(
            row=row,
            address_rows=addresses,
        )

    # ------------------------------------------------------------
    # Backward-compatible aliases
    # ------------------------------------------------------------

    async def get_all(self) -> tuple[Token, ...]:
        """
        Backward-compatible alias for resolve_all().
        """

        return await self.resolve_all()

    async def get_enabled(self) -> tuple[Token, ...]:
        """
        Backward-compatible alias for resolve_enabled().
        """

        return await self.resolve_enabled()

    async def get_by_symbol(
        self,
        symbol: str,
    ) -> Token | None:
        """
        Backward-compatible alias for resolve_by_symbol().
        """

        return await self.resolve_by_symbol(symbol)

    # ------------------------------------------------------------
    # Internal resolution
    # ------------------------------------------------------------

    async def _resolve_rows(
        self,
        rows: Sequence[Any],
        chain_id: int | None,
    ) -> tuple[Token, ...]:
        if rows is None:
            raise TokenError(
                "Token repository returned None."
            )

        result: list[Token] = []

        for row in rows:
            token_id = self._row_value(
                row,
                "id",
                0,
            )

            addresses = await self._get_addresses(
                token_id,
                chain_id=chain_id,
            )

            # A chain-specific resolution is scanner-oriented:
            # tokens without an address on that chain are not usable.
            if chain_id is not None and not addresses:
                continue

            result.append(
                self._build_token(
                    row=row,
                    address_rows=addresses,
                )
            )

        return tuple(result)

    async def _get_addresses(
        self,
        token_id: Any,
        chain_id: int | None = None,
    ) -> list[Any]:
        if token_id is None:
            raise TokenError(
                "Token row does not contain an id."
            )

        try:
            return await self._repository.get_addresses(
                int(token_id),
                chain_id=chain_id,
            )
        except TypeError:
            # Compatibility with repositories exposing the older
            # positional form:
            #
            # get_addresses(token_id, chain_id)
            #
            # This keeps the resolver compatible with both forms.
            return await self._repository.get_addresses(
                int(token_id),
                chain_id,
            )

    def _build_token(
        self,
        row: Any,
        address_rows: Sequence[Any],
    ) -> Token:
        try:
            addresses = tuple(
                self._build_address(address_row)
                for address_row in address_rows
            )

            return Token(
                symbol=str(
                    self._row_value(
                        row,
                        "symbol",
                        1,
                    )
                ),
                name=str(
                    self._row_value(
                        row,
                        "name",
                        2,
                    )
                ),
                coingecko_id=str(
                    self._row_value(
                        row,
                        "coingecko_id",
                        3,
                    )
                ),
                enabled=bool(
                    self._row_value(
                        row,
                        "enabled",
                        4,
                    )
                ),
                priority=int(
                    self._row_value(
                        row,
                        "priority",
                        5,
                    )
                ),
                addresses=addresses,
            )

        except TokenError:
            raise

        except Exception as error:
            raise TokenError(
                "Failed to build Token model."
            ) from error

    @staticmethod
    def _build_address(
        row: Any,
    ) -> TokenAddress:
        try:
            return TokenAddress(
                chain_id=int(
                    TokenResolver._row_value(
                        row,
                        "chain_id",
                        2,
                    )
                ),
                address=str(
                    TokenResolver._row_value(
                        row,
                        "address",
                        3,
                    )
                ),
                decimals=int(
                    TokenResolver._row_value(
                        row,
                        "decimals",
                        4,
                    )
                ),
                availability=bool(
                    TokenResolver._row_value(
                        row,
                        "availability",
                        5,
                    )
                ),
            )

        except Exception as error:
            raise TokenError(
                "Failed to build TokenAddress model."
            ) from error

    @staticmethod
    def _row_value(
        row: Any,
        key: str,
        index: int,
    ) -> Any:
        """
        Read a value from several supported row formats.

        Supported:
            1. mapping rows: row["symbol"]
            2. objects with attributes: row.symbol
            3. sequence/SQLite rows: row[index]
        """

        if row is None:
            raise TokenError(
                "Repository returned an empty token row."
            )

        if isinstance(row, Mapping):
            if key not in row:
                raise TokenError(
                    f"Token row is missing '{key}'."
                )

            return row[key]

        try:
            return getattr(row, key)
        except AttributeError:
            pass

        try:
            return row[index]
        except (IndexError, KeyError, TypeError) as error:
            raise TokenError(
                f"Token row is missing '{key}'."
            ) from error
