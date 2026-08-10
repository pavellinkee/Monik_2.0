"""
Stage 2 scan result model.

Responsibility:
    Represents one reverse quote produced from a Stage 1 quote.

Stage 2 verifies the second leg of a potential round trip:

    base token
        |
        | Stage 1
        v
    target token
        |
        | Stage 2
        v
    base token

This model does NOT:
    - calculate profitability;
    - calculate gas costs;
    - validate arbitrage;
    - communicate with external services;
    - access the database.

Compatibility:
    The model keeps the same immutable Pydantic model foundation
    used by the existing Stage1ScanResult.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from aggregators.quote import Quote
from models.base_model import BaseModel


class Stage2ScanResult(BaseModel):
    """
    Immutable result of one Stage 2 reverse quote.

    A result represents:

        stage1_quote.aggregator -> stage2_quote.aggregator

    where the Stage 2 input amount is exactly the output amount
    produced by the Stage 1 quote.
    """

    chain_id: int

    base_symbol: str
    target_symbol: str

    amount_usdt: Decimal

    buy_aggregator: str
    sell_aggregator: str

    stage1_quote: Quote
    stage2_quote: Quote

    class Config:
        frozen = True

    def __init__(self, **data):
        """
        Validate cross-field invariants while keeping compatibility
        with the project's existing Pydantic BaseModel.
        """
        super().__init__(**data)

        if self.stage1_quote.chain_id != self.chain_id:
            raise ValueError(
                "Stage 1 quote chain_id does not match "
                "the result chain_id."
            )

        if self.stage2_quote.chain_id != self.chain_id:
            raise ValueError(
                "Stage 2 quote chain_id does not match "
                "the result chain_id."
            )

        if self.stage1_quote.aggregator != self.buy_aggregator:
            raise ValueError(
                "buy_aggregator does not match the Stage 1 quote."
            )

        if self.stage2_quote.aggregator != self.sell_aggregator:
            raise ValueError(
                "sell_aggregator does not match the Stage 2 quote."
            )

        if (
            self.stage2_quote.token_in.lower()
            != self.stage1_quote.token_out.lower()
        ):
            raise ValueError(
                "Stage 2 token_in must equal Stage 1 token_out."
            )

        if (
            self.stage2_quote.token_out.lower()
            != self.stage1_quote.token_in.lower()
        ):
            raise ValueError(
                "Stage 2 token_out must equal Stage 1 token_in."
            )

        if self.stage2_quote.amount_in != self.stage1_quote.amount_out:
            raise ValueError(
                "Stage 2 amount_in must equal "
                "Stage 1 amount_out."
            )

        if self.stage1_quote.amount_out <= 0:
            raise ValueError(
                "Stage 1 amount_out must be greater than zero."
            )

        if self.stage2_quote.amount_out <= 0:
            raise ValueError(
                "Stage 2 amount_out must be greater than zero."
            )

    @property
    def round_trip_amount_out(self) -> int:
        """
        Return the final base-token amount after Stage 2.

        This is deliberately NOT a profit calculation.
        """
        return self.stage2_quote.amount_out
