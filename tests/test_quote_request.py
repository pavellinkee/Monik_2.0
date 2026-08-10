"""
Tests for the common QuoteRequest model.
"""

import pytest

from aggregators.quote_request import QuoteRequest


def test_quote_request_accepts_valid_data():
    """Valid quote request is created successfully."""

    request = QuoteRequest(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1000000000,
        token_in_decimals=6,
        token_out_decimals=18,
        requester_address="0xRequester",
    )

    assert request.chain_id == 137
    assert request.token_in == "0xTokenIn"
    assert request.token_out == "0xTokenOut"
    assert request.amount == 1000000000
    assert request.token_in_decimals == 6
    assert request.token_out_decimals == 18
    assert request.requester_address == "0xRequester"


def test_quote_request_allows_optional_fields():
    """Aggregator-specific fields may be omitted."""

    request = QuoteRequest(
        chain_id=1,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=100,
    )

    assert request.token_in_decimals is None
    assert request.token_out_decimals is None
    assert request.requester_address is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"chain_id": 0},
        {"chain_id": -1},
        {"token_in": ""},
        {"token_out": ""},
        {"amount": 0},
        {"amount": -1},
        {"token_in_decimals": -1},
        {"token_out_decimals": -1},
    ],
)
def test_quote_request_rejects_invalid_data(kwargs):
    """Invalid common request data is rejected."""

    base = {
        "chain_id": 1,
        "token_in": "0xTokenIn",
        "token_out": "0xTokenOut",
        "amount": 100,
    }

    base.update(kwargs)

    with pytest.raises(ValueError):
        QuoteRequest(**base)
