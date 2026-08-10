"""
Tests for ScannerEngine.
"""

from decimal import Decimal

import pytest

from aggregators.aggregator_engine import (
    AggregatorEngine,
)
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
from core.scanner_engine import ScannerEngine
from models.token import Token
from models.token_address import TokenAddress


class FakeTokenResolver:
    """Resolver using the new interface."""

    def __init__(self):
        self.usdt = Token(
            symbol="USDT",
            name="Tether USD",
            coingecko_id="tether",
            priority=1,
            addresses=(
                TokenAddress(
                    chain_id=137,
                    address="0xUSDT",
                    decimals=6,
                ),
            ),
        )

        self.aave = Token(
            symbol="AAVE",
            name="Aave",
            coingecko_id="aave",
            priority=2,
            addresses=(
                TokenAddress(
                    chain_id=137,
                    address="0xAAVE",
                    decimals=18,
                ),
            ),
        )

        self.sand = Token(
            symbol="SAND",
            name="The Sandbox",
            coingecko_id="the-sandbox",
            priority=3,
            addresses=(
                TokenAddress(
                    chain_id=137,
                    address="0xSAND",
                    decimals=18,
                ),
            ),
        )

    async def resolve_for_chain(
        self,
        chain_id: int,
    ):
        return (
            (
                self.usdt,
                self.usdt.addresses[0],
            ),
            (
                self.aave,
                self.aave.addresses[0],
            ),
            (
                self.sand,
                self.sand.addresses[0],
            ),
        )


class LegacyTokenResolver:
    """Resolver using the legacy interface."""

    def __init__(
        self,
        resolver: FakeTokenResolver,
    ):
        self._resolver = resolver

    async def get_enabled_on_chain(
        self,
        chain_id: int,
    ):
        return await self._resolver.resolve_for_chain(
            chain_id
        )


class FakeAggregator(AggregatorInterface):
    """
    Fake aggregator compatible with the current
    AggregatorInterface.
    """

    def __init__(
        self,
        name: str,
        multiplier: int,
    ):
        self._name = name
        self._multiplier = multiplier

    @property
    def name(self) -> str:
        return self._name

    @property
    def official_url(self) -> str:
        return "https://example.com"

    async def get_quote(
        self,
        request: QuoteRequest,
    ) -> Quote:
        return Quote(
            aggregator=self._name,
            chain_id=request.chain_id,
            token_in=request.token_in,
            token_out=request.token_out,
            amount_in=request.amount,
            amount_out=(
                request.amount
                * self._multiplier
            ),
            gas_estimate=None,
            gas_cost_native=None,
            price_impact=None,
            route=None,
            timestamp="test",
        )

    async def is_available(self) -> bool:
        return True


def build_aggregator_engine():
    """
    Build an AggregatorEngine with fake aggregators.

    The test adapters implement the same interface as
    production aggregators.
    """

    instances = AggregatorInstanceRegistry()

    limiters = {}

    for name, multiplier in (
        ("1inch", 2),
        ("0x", 3),
    ):
        instances.register(
            name,
            FakeAggregator(
                name=name,
                multiplier=multiplier,
            ),
        )

        limiters[name] = RateLimiter(
            standard_interval=0,
            max_interval=1,
            backoff_multiplier=2,
        )

    queues = AggregatorQueuePool.from_limiters(
        limiters
    )

    return AggregatorEngine(
        instances=instances,
        queues=queues,
    )


@pytest.mark.asyncio
async def test_stage1_builds_quotes_for_each_target():
    """Stage 1 creates quote requests for all target tokens."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
        base_symbol="USDT",
    )

    results = await engine.scan_stage1(
        chain_id=137,
        amount_usdt=Decimal("100"),
    )

    assert len(results) == 2

    assert [
        result.target_symbol
        for result in results
    ] == [
        "AAVE",
        "SAND",
    ]


@pytest.mark.asyncio
async def test_stage1_converts_usdt_to_smallest_units():
    """USDT amount is converted using its six decimals."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    results = await engine.scan_stage1(
        chain_id=137,
        amount_usdt=Decimal("100"),
        max_tokens=1,
    )

    result = results[0]

    assert result.amount_usdt == Decimal("100")
    assert result.amount_in_base_units == 100_000_000
    assert result.base_decimals == 6
    assert result.target_decimals == 18


@pytest.mark.asyncio
async def test_stage1_collects_quotes_from_all_aggregators():
    """Every configured aggregator receives the same request."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    results = await engine.scan_stage1(
        chain_id=137,
        amount_usdt=Decimal("10"),
        max_tokens=1,
    )

    result = results[0]

    assert [
        quote.aggregator
        for quote in result.quotes
    ] == [
        "1inch",
        "0x",
    ]

    assert result.quotes[0].amount_in == 10_000_000
    assert result.quotes[1].amount_in == 10_000_000


@pytest.mark.asyncio
async def test_stage1_supports_token_resolver_legacy_interface():
    """Legacy get_enabled_on_chain() remains supported."""

    resolver = FakeTokenResolver()

    engine = ScannerEngine(
        token_resolver=LegacyTokenResolver(
            resolver
        ),
        aggregator_engine=build_aggregator_engine(),
    )

    results = await engine.scan_stage1(
        chain_id=137,
        amount_usdt=Decimal("1"),
        max_tokens=1,
    )

    assert len(results) == 1
    assert results[0].target_symbol == "AAVE"


@pytest.mark.asyncio
async def test_run_stage1_is_compatibility_alias():
    """run_stage1() delegates to scan_stage1()."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    results = await engine.run_stage1(
        chain_id=137,
        amount_usdt=Decimal("1"),
        max_tokens=1,
    )

    assert len(results) == 1


@pytest.mark.asyncio
async def test_stage1_can_limit_target_tokens():
    """max_tokens limits the number of targets."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    results = await engine.scan_stage1(
        chain_id=137,
        amount_usdt=Decimal("1"),
        max_tokens=1,
    )

    assert len(results) == 1
    assert results[0].target_symbol == "AAVE"


@pytest.mark.asyncio
async def test_stage1_rejects_invalid_chain():
    """Invalid chain IDs fail fast."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    with pytest.raises(
        ValueError,
        match="chain_id",
    ):
        await engine.scan_stage1(
            chain_id=0,
            amount_usdt=Decimal("1"),
        )


@pytest.mark.asyncio
async def test_stage1_rejects_invalid_amount():
    """Non-positive amounts fail fast."""

    engine = ScannerEngine(
        token_resolver=FakeTokenResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    with pytest.raises(
        ValueError,
        match="amount_usdt",
    ):
        await engine.scan_stage1(
            chain_id=137,
            amount_usdt=Decimal("0"),
        )


@pytest.mark.asyncio
async def test_stage1_rejects_missing_base_token():
    """Missing USDT on a network is an explicit error."""

    resolver = FakeTokenResolver()

    class ResolverWithoutUsdt:
        async def resolve_for_chain(
            self,
            chain_id: int,
        ):
            return (
                (
                    resolver.aave,
                    resolver.aave.addresses[0],
                ),
            )

    engine = ScannerEngine(
        token_resolver=ResolverWithoutUsdt(),
        aggregator_engine=build_aggregator_engine(),
    )

    with pytest.raises(
        Exception,
        match="USDT",
    ):
        await engine.scan_stage1(
            chain_id=137,
            amount_usdt=Decimal("1"),
        )


@pytest.mark.asyncio
async def test_stage1_returns_empty_when_no_targets():
    """A network containing only the base token has no targets."""

    resolver = FakeTokenResolver()

    class OnlyBaseResolver:
        async def resolve_for_chain(
            self,
            chain_id: int,
        ):
            return (
                (
                    resolver.usdt,
                    resolver.usdt.addresses[0],
                ),
            )

    engine = ScannerEngine(
        token_resolver=OnlyBaseResolver(),
        aggregator_engine=build_aggregator_engine(),
    )

    results = await engine.scan_stage1(
        chain_id=137,
        amount_usdt=Decimal("1"),
    )

    assert results == ()
