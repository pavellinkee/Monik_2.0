"""
Stage 1 scan result model.

Responsibility:
    Represents the immutable result of one Stage 1 token scan.

Does NOT:
    - calculate arbitrage;
    - calculate profitability;
    - calculate gas costs;
    - validate opportunities;
    - communicate with external services.
"""

from decimal import Decimal

from pydantic import Field

from aggregators.quote import Quote
from models.base_model import BaseModel


class Stage1ScanResult(BaseModel):
    """Immutable result of a Stage 1 scan for one token."""

    chain_id: int

    base_symbol: str
    target_symbol: str

    amount_usdt: Decimal
    amount_in_base_units: int

    base_decimals: int
    target_decimals: int

    quotes: tuple[Quote, ...] = Field(
        min_length=1,
    )
