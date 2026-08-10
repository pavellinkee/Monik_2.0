"""
Token resolver.

Responsibility:
    Converts token repository data into immutable
    domain models used by the scanner.

Does NOT:
    - access the database directly;
    - perform API requests;
    - cache token data;
    - calculate prices;
    - calculate arbitrage;
    - communicate with aggregators;
    - send Telegram messages.

Compatibility:
    The resolver keeps the existing get_* interface and also
    exposes the newer resolve_* interface.

    Both interfaces use the same internal implementation.
"""

from __future__ import annotations

from typing import Any

from models.token import Token
from models.token_address import TokenAddress
from repositories.token_repository import TokenRepository


class TokenResolver:
    """
    Resolve database token records into Token models.

    No caching is performed. Every resolution reflects
    the current repository state.
    """

    def __init__(
        self,
        repository: TokenRepository,
    ) -> None:
        self._repository = repository

    # ============================================================
    # Current / legacy public interface
    # ============================================================

    async def get_enabled_tokens(
        self,
    ) -> tuple[Token, ...]:
        """
        Return all enabled tokens with their available
        blockchain addresses.

        Tokens remain ordered according to the repository
        priority ordering.
        """

        rows = await self._repository.get_enabled()

        return await self._resolve_rows(
            rows
        )

    async def get_by_symbol(
        self,
        symbol: str,
    ) -> Token | None:
        """
        Resolve an enabled token by symbol.

        Returns None when:
            - the token does not exist;
            - the token is disabled.

        Symbol matching is case-insensitive.
        """

        normalized_symbol = self._normalize_symbol(
            symbol
        )

        row = await self._repository.get_by_symbol(
            normalized_symbol
        )

        if row is None:
            if normalized_symbol != symbol:
                row = await self._repository.get_by_symbol(
                    symbol
                )

        if row is None:
            return None

        if not self._row_enabled(row):
            return None

        return await self._build_token(
            row
        )

    async def get_on_chain(
        self,
        symbol: str,
        chain_id: int,
    ) -> TokenAddress | None:
        """
        Resolve a token address on a specific network.

        Returns None when the token or available address
        does not exist.
        """

        normalized_symbol = self._normalize_symbol(
            symbol
        )

        self._validate_chain_id(
            chain_id
        )

        row = await self._repository.get_by_symbol(
            normalized_symbol
        )

        if row is None:
            if normalized_symbol != symbol:
                row = await self._repository.get_by_symbol(
                    symbol
                )

        if row is None:
            return None

        if not self._row_enabled(row):
            return None

        token_id = self._token_id(
            row
        )

        address_row = (
            await self._repository.get_token_with_address(
                token_id,
                chain_id,
            )
        )

        if address_row is None:
            return None

        return self._build_token_address_from_joined_row(
            address_row
        )

    async def get_token_and_address(
        self,
        symbol: str,
        chain_id: int,
    ) -> tuple[Token, TokenAddress] | None:
        """
        Resolve both the logical token and its address
        on a specific network.
        """

        token = await self.get_by_symbol(
            symbol
        )

        if token is None:
            return None

        address = await self.get_on_chain(
            symbol,
            chain_id,
        )

        if address is None:
            return None

        return token, address

    async def get_enabled_on_chain(
        self,
        chain_id: int,
    ) -> tuple[tuple[Token, TokenAddress], ...]:
        """
        Return every enabled token that has an available
        address on the requested network.

        The result follows token priority order.
        """

        self._validate_chain_id(
            chain_id
        )

        tokens = await self.get_enabled_tokens()

        result: list[
            tuple[Token, TokenAddress]
        ] = []

        for token in tokens:
            address = next(
                (
                    item
                    for item in token.addresses
                    if (
                        item.chain_id == chain_id
                        and item.availability
                    )
                ),
                None,
            )

            if address is not None:
                result.append(
                    (
                        token,
                        address,
                    )
                )

        return tuple(result)

    # ============================================================
    # New public interface
    # ============================================================

    async def resolve_all(
        self,
    ) -> tuple[Token, ...]:
        """
        Resolve all tokens from the repository.

        This is the new general-purpose resolver interface.
        """

        rows = await self._repository.get_all()

        return await self._resolve_rows(
            rows
        )

    async def resolve_enabled(
        self,
    ) -> tuple[Token, ...]:
        """
        Resolve enabled tokens.

        Equivalent to get_enabled_tokens().
        """

        return await self.get_enabled_tokens()

    async def resolve_by_symbol(
        self,
        symbol: str,
    ) -> Token | None:
        """
        Resolve one enabled token by symbol.

        Equivalent to get_by_symbol().
        """

        return await self.get_by_symbol(
            symbol
        )

    async def resolve_for_chain(
        self,
        chain_id: int,
    ) -> tuple[
        tuple[Token, TokenAddress],
        ...,
    ]:
        """
        Resolve enabled tokens and their available
        addresses on a specific blockchain network.

        Equivalent to get_enabled_on_chain().
        """

        return await self.get_enabled_on_chain(
            chain_id
        )

    # ============================================================
    # Internal resolution
    # ============================================================

    async def _resolve_rows(
        self,
        rows: list[Any],
    ) -> tuple[Token, ...]:
        """
        Convert repository token rows into Token models.
        """

        tokens: list[Token] = []

        for row in rows:
            token = await self._build_token(
                row
            )

            tokens.append(
                token
            )

        return tuple(tokens)

    async def _build_token(
        self,
        row: Any,
    ) -> Token:
        """
        Build an immutable Token from a repository row.
        """

        token_id = self._token_id(
            row
        )

        address_rows = (
            await self._repository.get_addresses(
                token_id
            )
        )

        addresses = tuple(
            self._build_token_address(
                address_row
            )
            for address_row in address_rows
        )

        return Token(
            symbol=self._token_symbol(
                row
            ),
            name=self._token_name(
                row
            ),
            coingecko_id=self._token_coingecko_id(
                row
            ),
            enabled=self._row_enabled(
                row
            ),
            priority=self._token_priority(
                row
            ),
            addresses=addresses,
        )

    # ============================================================
    # Address conversion
    # ============================================================

    @staticmethod
    def _build_token_address(
        row: Any,
    ) -> TokenAddress:
        """
        Convert a token_addresses database row
        into TokenAddress.
        """

        if not isinstance(
            row,
            (tuple, list),
        ):
            raise ValueError(
                "Token address repository row must "
                "be a tuple or list."
            )

        if len(row) < 6:
            raise ValueError(
                "Token address repository row is incomplete."
            )

        return TokenAddress(
            chain_id=int(
                row[2]
            ),
            address=str(
                row[3]
            ),
            decimals=int(
                row[4]
            ),
            availability=bool(
                row[5]
            ),
        )

    @staticmethod
    def _build_token_address_from_joined_row(
        row: Any,
    ) -> TokenAddress:
        """
        Convert a joined token/token_addresses row
        into TokenAddress.

        TokenRepository.get_token_with_address()
        returns:

            0  token.id
            1  token.symbol
            2  token.name
            3  token.coingecko_id
            4  token.enabled
            5  token.priority
            6  token_address.id
            7  chain_id
            8  address
            9  decimals
            10 availability
        """

        if not isinstance(
            row,
            (tuple, list),
        ):
            raise ValueError(
                "Joined token repository row must "
                "be a tuple or list."
            )

        if len(row) < 11:
            raise ValueError(
                "Joined token repository row is incomplete."
            )

        return TokenAddress(
            chain_id=int(
                row[7]
            ),
            address=str(
                row[8]
            ),
            decimals=int(
                row[9]
            ),
            availability=bool(
                row[10]
            ),
        )

    # ============================================================
    # Validation and row extraction
    # ============================================================

    @staticmethod
    def _normalize_symbol(
        symbol: str,
    ) -> str:
        """Normalize a token symbol."""

        if not isinstance(
            symbol,
            str,
        ):
            raise TypeError(
                "symbol must be a string."
            )

        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError(
                "symbol cannot be empty."
            )

        return normalized

    @staticmethod
    def _validate_chain_id(
        chain_id: int,
    ) -> None:
        """Validate blockchain network identifier."""

        if chain_id <= 0:
            raise ValueError(
                "chain_id must be greater than 0."
            )

    @staticmethod
    def _token_id(
        row: Any,
    ) -> int:
        """Extract token ID from a repository row."""

        if not isinstance(
            row,
            (tuple, list),
        ):
            raise ValueError(
                "Token repository row must "
                "be a tuple or list."
            )

        if len(row) < 1:
            raise ValueError(
                "Token repository row is empty."
            )

        return int(
            row[0]
        )

    @staticmethod
    def _token_symbol(
        row: Any,
    ) -> str:
        """Extract token symbol."""

        if len(row) < 2:
            raise ValueError(
                "Token repository row is incomplete."
            )

        return str(
            row[1]
        )

    @staticmethod
    def _token_name(
        row: Any,
    ) -> str:
        """Extract token name."""

        if len(row) < 3:
            raise ValueError(
                "Token repository row is incomplete."
            )

        return str(
            row[2]
        )

    @staticmethod
    def _token_coingecko_id(
        row: Any,
    ) -> str:
        """Extract CoinGecko identifier."""

        if len(row) < 4:
            raise ValueError(
                "Token repository row is incomplete."
            )

        return str(
            row[3]
        )

    @staticmethod
    def _row_enabled(
        row: Any,
    ) -> bool:
        """Extract enabled flag."""

        if len(row) < 5:
            raise ValueError(
                "Token repository row is incomplete."
            )

        return bool(
            row[4]
        )

    @staticmethod
    def _token_priority(
        row: Any,
    ) -> int:
        """Extract token priority."""

        if len(row) < 6:
            raise ValueError(
                "Token repository row is incomplete."
            )

        return int(
            row[5]
        )
