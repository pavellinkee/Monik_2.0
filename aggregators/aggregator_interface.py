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

from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest


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
        request: QuoteRequest,
    ) -> Quote:
        """
        Request a normalized quote from the aggregator.

        Aggregator-specific adapters decide which fields from
        QuoteRequest are required by their API.
        """

    @abstractmethod
    async def is_available(self) -> bool:
        """Check whether the aggregator API is currently available."""
