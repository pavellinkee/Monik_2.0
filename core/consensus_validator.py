"""
Consensus validator.

Responsibility:
    Determine whether a Stage 2 opportunity has sufficient
    independent aggregator confirmation.

The validator does NOT:
    - perform HTTP requests;
    - calculate gas;
    - calculate profit;
    - access the database;
    - send notifications.

Consensus is based only on already collected Stage 2 quotes.

This is important because the scanner must not create additional
requests merely to validate an opportunity.

Compatibility:
    validate()
    validate_result()
"""

from __future__ import annotations

from collections.abc import Iterable

from models.stage2_scan import Stage2ScanResult
from models.validation import ValidationResult


class ConsensusValidator:
    """
    Validates aggregator consensus for Stage 2 results.
    """

    def __init__(
        self,
        minimum_confirmations: int = 2,
    ) -> None:
        if minimum_confirmations <= 0:
            raise ValueError(
                "minimum_confirmations must be greater "
                "than zero."
            )

        self._minimum_confirmations = (
            minimum_confirmations
        )

    @property
    def minimum_confirmations(self) -> int:
        return self._minimum_confirmations

    def validate_result(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> ValidationResult:
        """
        Validate one opportunity against related Stage 2 results.

        A confirmation must:
            - belong to the same chain;
            - use the same base/target pair;
            - use the same Stage 1 buy aggregator;
            - represent the same initial amount;
            - come from a different sell aggregator.

        The candidate itself counts as one confirmation.
        """

        if not isinstance(
            result,
            Stage2ScanResult,
        ):
            raise TypeError(
                "result must be a Stage2ScanResult."
            )

        related = tuple(related_results)

        for item in related:
            if not isinstance(
                item,
                Stage2ScanResult,
            ):
                raise TypeError(
                    "related_results must contain only "
                    "Stage2ScanResult objects."
                )

        confirmations: set[str] = set()

        for item in related:
            if not self._same_opportunity_group(
                result,
                item,
            ):
                continue

            confirmations.add(
                item.sell_aggregator
            )

        confirmations.add(
            result.sell_aggregator
        )

        if (
            len(confirmations)
            < self._minimum_confirmations
        ):
            return ValidationResult(
                valid=False,
                validator="consensus",
                reason=(
                    "Insufficient independent aggregator "
                    "confirmation."
                ),
            )

        return ValidationResult(
            valid=True,
            validator="consensus",
            reason=None,
        )

    def validate(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> ValidationResult:
        """
        Legacy compatibility alias.
        """
        return self.validate_result(
            result=result,
            related_results=related_results,
        )

    @staticmethod
    def _same_opportunity_group(
        first: Stage2ScanResult,
        second: Stage2ScanResult,
    ) -> bool:
        return (
            first.chain_id
            == second.chain_id
            and first.base_symbol.upper()
            == second.base_symbol.upper()
            and first.target_symbol.upper()
            == second.target_symbol.upper()
            and first.buy_aggregator
            == second.buy_aggregator
            and first.amount_usdt
            == second.amount_usdt
            and first.stage1_quote.amount_in
            == second.stage1_quote.amount_in
        )
