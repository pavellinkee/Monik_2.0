"""
Tests for AggregatorEngine.
"""

import asyncio
from dataclasses import dataclass

import pytest

from aggregators.aggregator_interface import (
    AggregatorInterface,
)
from aggregators.instance_registry import (
    AggregatorInstanceRegistry,
)
from aggregators.quote import Quote
from aggregators.quote_request import QuoteRequest
from aggregators.queue_pool import (
    AggregatorQueuePool,
)
from aggregators.rate_limiter import RateLimiter
from aggregators.request_queue import (
    AggregatorRequestQueue,
)
from core.aggregator_engine import (
    AggregatorEngine,
)


@dataclass
class FakeAggregator(AggregatorInterface):
    """Fake aggregator used by engine tests."""

    aggregator_name: str
    output_amount: int
    delay_seconds: float = 0.0

    @property
    def name(self) -> str:
        """Return the fake aggregator name."""

        return self.aggregator_name

    @property
    def official_url(self) -> str:
        """Return the fake aggregator URL."""

        return "https://example.com"

    async def get_quote(
        self,
        request: QuoteRequest,
    ) -> Quote:
        """Return a deterministic fake quote."""

        if self.delay_seconds > 0:
            await asyncio.sleep(
                self.delay_seconds
            )

        return Quote(
            aggregator=self.name,
            chain_id=request.chain_id,
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount,
            amount_out=self.output_amount,
            gas_estimate=None,
            gas_cost_native=None,
            price_impact=None,
            route=None,
            timestamp="test",
        )

    async def is_available(self) -> bool:
        """Fake aggregator is always available."""

        return True


def build_engine(
    aggregators: list[FakeAggregator],
) -> AggregatorEngine:
    """Build an engine with real queues and limiters."""

    instances = AggregatorInstanceRegistry()

    limiters: dict[
        str,
        RateLimiter,
    ] = {}

    for aggregator in aggregators:
        instances.register(
            aggregator.name,
            aggregator,
        )

        limiters[
            aggregator.name
        ] = RateLimiter(
            initial_delay_seconds=0,
            max_delay_seconds=1,
            delay_multiplier=2,
        )

    queues = AggregatorQueuePool.from_limiters(
        limiters
    )

    return AggregatorEngine(
        instances=instances,
        queues=queues,
    )


def build_request() -> QuoteRequest:
    """Build a deterministic quote request."""

    return QuoteRequest(
        chain_id=137,
        token_in="0xTokenIn",
        token_out="0xTokenOut",
        amount=1_000_000,
    )


@pytest.mark.asyncio
async def test_get_quote_returns_quote():
    """Engine returns the quote produced by an aggregator."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    quote = await engine.get_quote(
        aggregator_name="1inch",
        request=build_request(),
        stage=1,
    )

    assert isinstance(
        quote,
        Quote,
    )

    assert quote.aggregator == "1inch"
    assert quote.amount_in == 1_000_000
    assert quote.amount_out == 1_250_000


@pytest.mark.asyncio
async def test_get_quote_supports_stage_2():
    """Stage 2 requests are accepted by the engine."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    quote = await engine.get_quote(
        aggregator_name="1inch",
        request=build_request(),
        stage=2,
    )

    assert quote.amount_out == 1_250_000


@pytest.mark.asyncio
async def test_get_quote_rejects_unknown_aggregator():
    """Unknown configured aggregators fail explicitly."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    with pytest.raises(
        KeyError,
        match="Unknown configured aggregator",
    ):
        await engine.get_quote(
            aggregator_name="Unknown",
            request=build_request(),
            stage=1,
        )


@pytest.mark.asyncio
async def test_get_quote_rejects_invalid_stage():
    """Only Stage 1 and Stage 2 are accepted."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    with pytest.raises(
        ValueError,
        match="stage",
    ):
        await engine.get_quote(
            aggregator_name="1inch",
            request=build_request(),
            stage=3,
        )


@pytest.mark.asyncio
async def test_get_quote_rejects_invalid_request():
    """Only QuoteRequest objects are accepted."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    with pytest.raises(
        TypeError,
        match="QuoteRequest",
    ):
        await engine.get_quote(
            aggregator_name="1inch",
            request="invalid",  # type: ignore[arg-type]
            stage=1,
        )


@pytest.mark.asyncio
async def test_get_quotes_queries_multiple_aggregators():
    """Multiple aggregators can be queried concurrently."""

    first = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    second = FakeAggregator(
        aggregator_name="0x",
        output_amount=1_300_000,
    )

    engine = build_engine(
        [
            first,
            second,
        ]
    )

    result = await engine.get_quotes(
        aggregator_names=[
            "1inch",
            "0x",
        ],
        request=build_request(),
        stage=1,
    )

    assert list(result.keys()) == [
        "1inch",
        "0x",
    ]

    assert result["1inch"].amount_out == 1_250_000
    assert result["0x"].amount_out == 1_300_000


@pytest.mark.asyncio
async def test_get_quotes_rejects_empty_aggregator_list():
    """An empty aggregator list is invalid."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    with pytest.raises(
        ValueError,
        match="At least one aggregator",
    ):
        await engine.get_quotes(
            aggregator_names=[],
            request=build_request(),
            stage=1,
        )


@pytest.mark.asyncio
async def test_get_quotes_rejects_duplicate_aggregators():
    """The same aggregator cannot be requested twice."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        await engine.get_quotes(
            aggregator_names=[
                "1inch",
                "1inch",
            ],
            request=build_request(),
            stage=1,
        )


@pytest.mark.asyncio
async def test_different_aggregators_can_execute_in_parallel():
    """Independent aggregator queues can execute concurrently."""

    first = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
        delay_seconds=0.1,
    )

    second = FakeAggregator(
        aggregator_name="0x",
        output_amount=1_300_000,
        delay_seconds=0.1,
    )

    engine = build_engine(
        [
            first,
            second,
        ]
    )

    started = asyncio.get_running_loop().time()

    result = await engine.get_quotes(
        aggregator_names=[
            "1inch",
            "0x",
        ],
        request=build_request(),
        stage=1,
    )

    elapsed = (
        asyncio.get_running_loop().time()
        - started
    )

    assert set(result.keys()) == {
        "1inch",
        "0x",
    }

    assert elapsed < 0.18


def test_contains_requires_instance_and_queue():
    """An aggregator is usable only when both layers exist."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    assert engine.contains("1inch") is True
    assert engine.contains("0x") is False


def test_names_returns_usable_aggregators():
    """Names contain only aggregators with complete wiring."""

    first = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    second = FakeAggregator(
        aggregator_name="0x",
        output_amount=1_300_000,
    )

    engine = build_engine(
        [
            first,
            second,
        ]
    )

    assert engine.names() == (
        "1inch",
        "0x",
    )


def test_get_instance_returns_configured_instance():
    """Engine exposes a configured aggregator instance."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    result = engine.get_instance(
        "1inch"
    )

    assert result is aggregator


def test_get_instance_rejects_unknown_aggregator():
    """Unknown instances raise KeyError."""

    aggregator = FakeAggregator(
        aggregator_name="1inch",
        output_amount=1_250_000,
    )

    engine = build_engine(
        [aggregator]
    )

    with pytest.raises(
        KeyError,
        match="Unknown configured aggregator",
    ):
        engine.get_instance(
            "Unknown"
        )
