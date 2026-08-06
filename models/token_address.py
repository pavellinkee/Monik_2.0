"""
TokenAddress model.

Responsibility:
    Represents a token contract on a specific blockchain network.

Does NOT:
    - contain market data;
    - calculate prices;
    - perform validation;
    - communicate with external services.
"""

from models.base_model import BaseModel


class TokenAddress(BaseModel):
    """
    Immutable token contract description.
    """

    chain_id: int
    address: str
    decimals: int
    availability: bool = True
