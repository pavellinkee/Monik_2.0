"""
Aggregator interface.

Responsibility:
    Defines the common interface for all supported aggregators.

Supported implementations:
    - 1inch
    - 0x
    - Uniswap
    - Velora

Does NOT:
    - control scanner stages;
    - control scheduling;
    - calculate global arbitrage opportunities;
    - send Telegram messages;
    - manage database repositories.
"""

from abc import ABC, abstractmethod
from typing import Any


class AggregatorInterface(ABC):
    """Common interface for all aggregator implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the internal aggregator identifier."""

    @property
    @abstractmethod
    def official_url(self) -> str:
        """Return the official aggregator website URL."""

    @abstractmethod
    async def get_quote(
        self,
        chain_id: int,
        token_in: str,
        token_out: str,
        amount: int,
    ) -> Any:
        """
        Request a quote from the aggregator.

        Args:
            chain_id:
                Blockchain network identifier.

            token_in:
                Address of the token being sold.

            token_out:
                Address of the token being received.

            amount:
                Amount of token_in in its smallest unit.
        """

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the aggregator API is currently available."""
