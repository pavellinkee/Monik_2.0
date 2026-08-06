"""
Token model.

Responsibility:
    Represents a logical token supported by the scanner.

Does NOT:
    - store prices;
    - calculate profits;
    - communicate with APIs;
    - perform validation.
"""

from models.base_model import BaseModel
from models.token_address import TokenAddress


class Token(BaseModel):
    """
    Immutable token description.
    """

    symbol: str
    name: str
    coingecko_id: str

    enabled: bool = True
    priority: int = 100

    addresses: tuple[TokenAddress, ...]
