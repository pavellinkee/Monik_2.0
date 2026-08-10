"""
Common quote request model.

Responsibility:
    Defines normalized input data required to request a quote
    from any supported aggregator.

Does NOT:
    - make API requests;
    - know aggregator-specific endpoints;
    - calculate arbitrage;
    - apply rate limits;
    - validate aggregator-specific requirements.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class QuoteRequest:
    """Normalized request data for an aggregator quote."""

    chain_id: int

    token_in: str
    token_out: str

    amount: int

    token_in_decimals: int | None = None
    token_out_decimals: int | None = None

    requester_address: str | None = None

    def __post_init__(self) -> None:
        """Validate common request requirements."""

        if self.chain_id <= 0:
            raise ValueError(
                "chain_id must be greater than 0."
            )

        if not self.token_in:
            raise ValueError(
                "token_in is required."
            )

        if not self.token_out:
            raise ValueError(
                "token_out is required."
            )

        if self.amount <= 0:
            raise ValueError(
                "amount must be greater than 0."
            )

        if (
            self.token_in_decimals is not None
            and self.token_in_decimals < 0
        ):
            raise ValueError(
                "token_in_decimals must be >= 0."
            )

        if (
            self.token_out_decimals is not None
            and self.token_out_decimals < 0
        ):
            raise ValueError(
                "token_out_decimals must be >= 0."
            )
