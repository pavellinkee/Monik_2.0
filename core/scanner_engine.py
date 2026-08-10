"""
Scanner engine.

Responsibility:
    Coordinates Stage 1 scanning between the token system
    and AggregatorEngine.

Stage 1 flow:

    TokenResolver
         |
         v
    available tokens on chain
         |
         v
    build QuoteRequest
         |
         v
    AggregatorEngine
         |
         v
    normalized Quotes
         |
         v
    Stage1ScanResult

Does NOT:
    - calculate arbitrage;
    - calculate profitability;
    - calculate gas costs;
    - validate opportunities;
    - manage rate limits;
    - manage request queues;
    - access the database directly;
    - send Telegram messages;
    - schedule recurring scans.

Compatibility:
    Supports both the current TokenResolver interface and
    the previous get_* interface.

    Current:
        resolve_for_chain()

    Legacy:
        get_enabled_on_chain()
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from decimal import Decimal

from aggregators.aggregator_engine import (
    AggregatorEngine,
)
from aggregators.quote_request import QuoteRequest
from core.exceptions import TokenError
from models.stage1_scan import Stage1ScanResult
from models.token import Token
from models.token_address import TokenAddress


class ScannerEngine:
    """
    Coordinates scanner stages without implementing their
    business calculations.

    Stage 1 currently creates normalized quote requests and
    collects quotes for each enabled target token.
    """

    def __init__(
        self,
        token_resolver,
        aggregator_engine: AggregatorEngine,
        base_symbol: str = "USDT",
        requester_address: str | None = None,
    ) -> None:
        if token_resolver is None:
            raise TypeError(
                "token_resolver is required."
            )

        if not isinstance(
            aggregator_engine,
            AggregatorEngine,
        ):
            raise TypeError(
                "aggregator_engine must be an "
                "AggregatorEngine."
            )

        if not isinstance(
            base_symbol,
            str,
        ):
            raise TypeError(
                "base_symbol must be a string."
            )

        normalized_base_symbol = (
            base_symbol.strip().upper()
        )

        if not normalized_base_symbol:
            raise ValueError(
                "base_symbol cannot be empty."
            )

        self._token_resolver = token_resolver
        self._aggregator_engine = aggregator_engine
        self._base_symbol = normalized_base_symbol
        self._requester_address = requester_address

    async def scan_stage1(
        self,
        chain_id: int,
        amount_usdt: Decimal,
        max_tokens: int | None = None,
    ) -> tuple[Stage1ScanResult, ...]:
        """
        Run Stage 1 for one blockchain network.

        The base token is the configured base_symbol, normally USDT.
        Every other enabled token available on the network becomes
        a Stage 1 target.

        max_tokens:
            Optional limit for the number of target tokens.
            None means all available targets.

        No profitability decision is made here.
        """

        self._validate_chain_id(
            chain_id
        )

        normalized_amount = (
            self._normalize_amount(
                amount_usdt
            )
        )

        if (
            max_tokens is not None
            and max_tokens <= 0
        ):
            raise ValueError(
                "max_tokens must be greater than 0."
            )

        token_pairs = (
            await self._resolve_tokens_for_chain(
                chain_id
            )
        )

        base_token, base_address = (
            self._find_base_token(
                token_pairs
            )
        )

        targets = [
            (
                token,
                address,
            )
            for token, address in token_pairs
            if token.symbol.upper()
            != self._base_symbol
        ]

        if max_tokens is not None:
            targets = targets[:max_tokens]

        if not targets:
            return ()

        amount_in_base_units = (
            self._to_base_units(
                normalized_amount,
                base_address.decimals,
            )
        )

        aggregator_names = (
            self._aggregator_engine.names()
        )

        if not aggregator_names:
            raise ValueError(
                "No configured aggregators are available."
            )

        tasks = [
            self._scan_target(
                base_token=base_token,
                base_address=base_address,
                target_token=target_token,
                target_address=target_address,
                chain_id=chain_id,
                amount_usdt=normalized_amount,
                amount_in_base_units=(
                    amount_in_base_units
                ),
                aggregator_names=aggregator_names,
            )
            for target_token, target_address
            in targets
        ]

        results = await asyncio.gather(
            *tasks
        )

        return tuple(results)

    async def run_stage1(
        self,
        chain_id: int,
        amount_usdt: Decimal,
        max_tokens: int | None = None,
    ) -> tuple[Stage1ScanResult, ...]:
        """
        Compatibility alias for scan_stage1().

        This allows callers using the alternative run_* naming
        convention to use the same implementation.
        """

        return await self.scan_stage1(
            chain_id=chain_id,
            amount_usdt=amount_usdt,
            max_tokens=max_tokens,
        )

    async def _scan_target(
        self,
        base_token: Token,
        base_address: TokenAddress,
        target_token: Token,
        target_address: TokenAddress,
        chain_id: int,
        amount_usdt: Decimal,
        amount_in_base_units: int,
        aggregator_names: Iterable[str],
    ) -> Stage1ScanResult:
        """Create one Stage 1 request and collect its quotes."""

        request = QuoteRequest(
            chain_id=chain_id,
            token_in=base_address.address,
            token_out=target_address.address,
            amount=amount_in_base_units,
            token_in_decimals=base_address.decimals,
            token_out_decimals=target_address.decimals,
            requester_address=self._requester_address,
        )

        quotes = await self._aggregator_engine.get_quotes(
            aggregator_names=aggregator_names,
            request=request,
            stage=1,
        )

        ordered_quotes = tuple(
            quotes[name]
            for name in aggregator_names
        )

        return Stage1ScanResult(
            chain_id=chain_id,
            base_symbol=base_token.symbol,
            target_symbol=target_token.symbol,
            amount_usdt=amount_usdt,
            amount_in_base_units=amount_in_base_units,
            base_decimals=base_address.decimals,
            target_decimals=target_address.decimals,
            quotes=ordered_quotes,
        )

    async def _resolve_tokens_for_chain(
        self,
        chain_id: int,
    ) -> tuple[
        tuple[Token, TokenAddress],
        ...,
    ]:
        """
        Resolve available tokens using the newest interface first.

        Legacy compatibility:
            get_enabled_on_chain()
        """

        resolver = self._token_resolver

        resolve_method = getattr(
            resolver,
            "resolve_for_chain",
            None,
        )

        if callable(resolve_method):
            result = await resolve_method(
                chain_id
            )

            return tuple(result)

        legacy_method = getattr(
            resolver,
            "get_enabled_on_chain",
            None,
        )

        if callable(legacy_method):
            result = await legacy_method(
                chain_id
            )

            return tuple(result)

        raise TypeError(
            "Token resolver does not provide either "
            "resolve_for_chain() or "
            "get_enabled_on_chain()."
        )

    def _find_base_token(
        self,
        token_pairs: tuple[
            tuple[Token, TokenAddress],
            ...,
        ],
    ) -> tuple[Token, TokenAddress]:
        """Find the configured base token."""

        for token, address in token_pairs:
            if (
                token.symbol.upper()
                == self._base_symbol
                and address.availability
            ):
                return token, address

        raise TokenError(
            f"Base token '{self._base_symbol}' "
            "is not available on the requested chain."
        )

    @staticmethod
    def _normalize_amount(
        amount_usdt: Decimal,
    ) -> Decimal:
        """Normalize and validate the scan amount."""

        try:
            amount = Decimal(
                str(amount_usdt)
            )
        except Exception as error:
            raise ValueError(
                "amount_usdt must be a valid decimal amount."
            ) from error

        if amount <= 0:
            raise ValueError(
                "amount_usdt must be greater than 0."
            )

        return amount

    @staticmethod
    def _to_base_units(
        amount: Decimal,
        decimals: int,
    ) -> int:
        """Convert human-readable token amount to smallest units."""

        if decimals < 0:
            raise ValueError(
                "Token decimals cannot be negative."
            )

        multiplier = Decimal(10) ** decimals

        raw_amount = (
            amount * multiplier
        )

        integral_amount = (
            raw_amount.to_integral_value()
        )

        if raw_amount != integral_amount:
            raise ValueError(
                "amount_usdt has more precision than "
                "the base token supports."
            )

        return int(
            integral_amount
        )

    @staticmethod
    def _validate_chain_id(
        chain_id: int,
    ) -> None:
        """Validate a blockchain network identifier."""

        if chain_id <= 0:
            raise ValueError(
                "chain_id must be greater than 0."
            )
