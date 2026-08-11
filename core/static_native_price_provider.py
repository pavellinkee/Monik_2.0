"""
Static native-token price provider.

Intended for:
    - tests;
    - development;
    - integration without external price APIs.

Production should use a real market-data source.
"""

from __future__ import annotations

from decimal import Decimal

from core.native_price_provider import (
    NativePriceProvider,
)


class StaticNativePriceProvider(
    NativePriceProvider
):
    """
    Returns configured native-token prices.
    """

    def __init__(
        self,
        prices: dict[int, Decimal | str | float],
    ) -> None:
        if not prices:
            raise ValueError(
                "prices must not be empty."
            )

        self._prices = {
            int(chain_id): Decimal(
                str(price)
            )
            for chain_id, price
            in prices.items()
        }

        for chain_id, price in self._prices.items():
            if chain_id <= 0:
                raise ValueError(
                    "chain_id must be greater than zero."
                )

            if price <= 0:
                raise ValueError(
                    "native-token price must be "
                    "greater than zero."
                )

    async def get_price(
        self,
        chain_id: int,
    ) -> Decimal:
        """
        Return configured price.
        """

        if chain_id not in self._prices:
            raise KeyError(
                f"No native-token price configured "
                f"for chain {chain_id}."
            )

        return self._prices[
            chain_id
        ]

    async def price(
        self,
        chain_id: int,
    ) -> Decimal:
        """
        Compatibility alias.
        """

        return await self.get_price(
            chain_id
        )
