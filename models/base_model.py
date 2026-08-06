"""
Base immutable model for the DEX Arbitrage Scanner.

Responsibility:
    Provides a common immutable base class for all project models.

Does NOT:
    - contain business logic;
    - perform calculations;
    - communicate with external services;
    - access the database.

Every project model should inherit from BaseModel.
"""

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    """
    Common immutable base model.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=False,
        str_strip_whitespace=True,
    )
