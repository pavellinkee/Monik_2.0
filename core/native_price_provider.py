"""
Native-token price provider interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class NativePriceProvider(ABC):
    """
    Interface for native-token USDT price retrieval.
    """

    @abstractmethod
    async def get_price(
        self,
        chain_id: int,
    ) -> Decimal:
        """
        Return native-token price in USDT.
        """
        raise NotImplementedError

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
