"""
Tests for TokenResolver.
"""

from unittest.mock import AsyncMock

import pytest

from models.token import Token
from models.token_address import TokenAddress
from repositories.token_repository import TokenRepository
from tokens.resolver import TokenResolver


def token_row(
    token_id: int = 1,
    symbol: str = "USDT",
    name: str = "Tether USD",
    coingecko_id: str = "tether",
    enabled: int = 1,
    priority: int = 1,
) -> tuple:
    """Build a token repository row."""

    return (
        token_id,
        symbol,
        name,
        coingecko_id,
        enabled,
        priority,
    )


def address_row(
    token_id: int = 1,
    chain_id: int = 137,
    address: str = "0xUSDT",
    decimals: int = 6,
    availability: int = 1,
) -> tuple:
    """Build a token address repository row."""

    return (
        1,
        token_id,
        chain_id,
        address,
        decimals,
        availability,
    )


def joined_row(
    token_id: int = 1,
    symbol: str = "USDT",
    name: str = "Tether USD",
    coingecko_id: str = "tether",
    enabled: int = 1,
    priority: int = 1,
    chain_id: int = 137,
    address: str = "0xUSDT",
    decimals: int = 6,
    availability: int = 1,
) -> tuple:
    """Build a joined token/address repository row."""

    return (
        token_id,
        symbol,
        name,
        coingecko_id,
        enabled,
        priority,
        1,
        chain_id,
        address,
        decimals,
        availability,
    )


@pytest.mark.asyncio
async def test_get_enabled_tokens_builds_domain_models():
    """Enabled database rows become Token models."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_enabled.return_value = [
        token_row()
    ]

    repository.get_addresses.return_value = [
        address_row()
    ]

    resolver = TokenResolver(repository)

    result = await resolver.get_enabled_tokens()

    assert len(result) == 1

    token = result[0]

    assert isinstance(token, Token)
    assert token.symbol == "USDT"
    assert token.name == "Tether USD"
    assert token.coingecko_id == "tether"
    assert token.enabled is True
    assert token.priority == 1

    assert len(token.addresses) == 1

    address = token.addresses[0]

    assert isinstance(address, TokenAddress)
    assert address.chain_id == 137
    assert address.address == "0xUSDT"
    assert address.decimals == 6
    assert address.availability is True


@pytest.mark.asyncio
async def test_get_enabled_tokens_preserves_repository_order():
    """Token priority order is preserved."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_enabled.return_value = [
        token_row(
            token_id=1,
            symbol="USDT",
            priority=1,
        ),
        token_row(
            token_id=2,
            symbol="USDC",
            priority=2,
        ),
    ]

    repository.get_addresses.side_effect = [
        [address_row(token_id=1)],
        [address_row(token_id=2)],
    ]

    resolver = TokenResolver(repository)

    result = await resolver.get_enabled_tokens()

    assert [token.symbol for token in result] == [
        "USDT",
        "USDC",
    ]


@pytest.mark.asyncio
async def test_get_by_symbol_is_case_insensitive():
    """Symbol resolution accepts different letter cases."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = token_row()

    repository.get_addresses.return_value = [
        address_row()
    ]

    resolver = TokenResolver(repository)

    result = await resolver.get_by_symbol(
        "usdt"
    )

    assert result is not None
    assert result.symbol == "USDT"

    repository.get_by_symbol.assert_awaited_with(
        "USDT"
    )


@pytest.mark.asyncio
async def test_get_by_symbol_returns_none_for_missing_token():
    """Unknown symbols return None."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = None

    resolver = TokenResolver(repository)

    result = await resolver.get_by_symbol(
        "UNKNOWN"
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_by_symbol_returns_none_for_disabled_token():
    """Disabled tokens are not exposed by the resolver."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = token_row(
        enabled=0
    )

    resolver = TokenResolver(repository)

    result = await resolver.get_by_symbol(
        "USDT"
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_on_chain_returns_token_address():
    """A token address is resolved for a network."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = token_row()

    repository.get_token_with_address.return_value = (
        joined_row()
    )

    resolver = TokenResolver(repository)

    result = await resolver.get_on_chain(
        "USDT",
        137,
    )

    assert isinstance(
        result,
        TokenAddress,
    )

    assert result.chain_id == 137
    assert result.address == "0xUSDT"
    assert result.decimals == 6
    assert result.availability is True


@pytest.mark.asyncio
async def test_get_on_chain_returns_none_without_address():
    """Missing network address returns None."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = token_row()

    repository.get_token_with_address.return_value = None

    resolver = TokenResolver(repository)

    result = await resolver.get_on_chain(
        "USDT",
        137,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_on_chain_returns_none_for_unknown_token():
    """Unknown token/network combinations return None."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = None

    resolver = TokenResolver(repository)

    result = await resolver.get_on_chain(
        "UNKNOWN",
        137,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_token_and_address_returns_pair():
    """Resolver can return logical token and network address."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_by_symbol.return_value = token_row()

    repository.get_addresses.return_value = [
        address_row()
    ]

    repository.get_token_with_address.return_value = (
        joined_row()
    )

    resolver = TokenResolver(repository)

    result = await resolver.get_token_and_address(
        "USDT",
        137,
    )

    assert result is not None

    token, address = result

    assert isinstance(token, Token)
    assert isinstance(address, TokenAddress)

    assert token.symbol == "USDT"
    assert address.chain_id == 137


@pytest.mark.asyncio
async def test_get_enabled_on_chain_filters_tokens_without_network():
    """Only tokens available on the requested network are returned."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_enabled.return_value = [
        token_row(
            token_id=1,
            symbol="USDT",
            priority=1,
        ),
        token_row(
            token_id=2,
            symbol="USDC",
            priority=2,
        ),
    ]

    repository.get_addresses.side_effect = [
        [
            address_row(
                token_id=1,
                chain_id=137,
            )
        ],
        [
            address_row(
                token_id=2,
                chain_id=1,
            )
        ],
    ]

    resolver = TokenResolver(repository)

    result = await resolver.get_enabled_on_chain(
        137
    )

    assert len(result) == 1

    token, address = result[0]

    assert token.symbol == "USDT"
    assert address.chain_id == 137


@pytest.mark.asyncio
async def test_get_enabled_on_chain_preserves_priority():
    """Network token results preserve token priority."""

    repository = AsyncMock(spec=TokenRepository)

    repository.get_enabled.return_value = [
        token_row(
            token_id=1,
            symbol="USDC",
            priority=1,
        ),
        token_row(
            token_id=2,
            symbol="USDT",
            priority=2,
        ),
    ]

    repository.get_addresses.side_effect = [
        [
            address_row(
                token_id=1,
                chain_id=137,
                address="0xUSDC",
            )
        ],
        [
            address_row(
                token_id=2,
                chain_id=137,
                address="0xUSDT",
            )
        ],
    ]

    resolver = TokenResolver(repository)

    result = await resolver.get_enabled_on_chain(
        137
    )

    assert [
        item[0].symbol
        for item in result
    ] == [
        "USDC",
        "USDT",
    ]


@pytest.mark.asyncio
async def test_invalid_chain_id_is_rejected():
    """Invalid network IDs fail fast."""

    repository = AsyncMock(spec=TokenRepository)

    resolver = TokenResolver(repository)

    with pytest.raises(
        ValueError,
        match="chain_id",
    ):
        await resolver.get_on_chain(
            "USDT",
            0,
        )


@pytest.mark.asyncio
async def test_invalid_symbol_is_rejected():
    """Empty symbols fail fast."""

    repository = AsyncMock(spec=TokenRepository)

    resolver = TokenResolver(repository)

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        await resolver.get_by_symbol(
            "   "
        )


def test_token_address_model_is_immutable():
    """Resolved domain models remain immutable."""

    address = TokenAddress(
        chain_id=137,
        address="0xUSDT",
        decimals=6,
    )

    with pytest.raises(
        Exception
    ):
        address.decimals = 18
