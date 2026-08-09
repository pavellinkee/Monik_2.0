"""
Aggregator errors.

Responsibility:
    Defines common errors for all aggregator implementations.

Does NOT:
    - send alerts;
    - change rate limits;
    - perform retries;
    - contain scanner logic.
"""


class AggregatorError(Exception):
    """Base error for all aggregator failures."""


class AggregatorUnavailableError(AggregatorError):
    """Aggregator API is temporarily unavailable."""


class AggregatorRateLimitError(AggregatorError):
    """Aggregator rate limit was reached."""


class AggregatorRequestError(AggregatorError):
    """Aggregator request failed."""


class AggregatorResponseError(AggregatorError):
    """Aggregator returned an invalid or unexpected response."""


class AggregatorConfigurationError(AggregatorError):
    """Aggregator configuration is invalid."""
