"""
Opportunity validation pipeline.

Responsibility:
    Combine deterministic integrity validation and aggregator
    consensus validation into one production validation step.

The pipeline does NOT:
    - request quotes;
    - calculate gas;
    - calculate profitability;
    - access the database;
    - send notifications.

Compatibility:
    validate()
    validate_opportunity()
"""

from __future__ import annotations

from collections.abc import Iterable

from core.consensus_validator import ConsensusValidator
from core.integrity_validator import IntegrityValidator
from models.stage2_scan import Stage2ScanResult
from models.validation import ValidationResult


class OpportunityValidator:
    """
    Final validation pipeline for Stage 2 opportunities.
    """

    def __init__(
        self,
        integrity_validator: IntegrityValidator | None = None,
        consensus_validator: ConsensusValidator | None = None,
    ) -> None:
        self._integrity_validator = (
            integrity_validator
            or IntegrityValidator()
        )

        self._consensus_validator = (
            consensus_validator
            or ConsensusValidator()
        )

    def validate_opportunity(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> tuple[ValidationResult, ...]:
        """
        Run all validation stages.

        Integrity is always executed first.

        Consensus is executed only when integrity succeeds.
        """

        integrity = (
            self._integrity_validator.validate_result(
                result
            )
        )

        if not integrity.valid:
            return (integrity,)

        consensus = (
            self._consensus_validator.validate_result(
                result=result,
                related_results=related_results,
            )
        )

        return (
            integrity,
            consensus,
        )

    def validate(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> tuple[ValidationResult, ...]:
        """
        Legacy compatibility alias.
        """
        return self.validate_opportunity(
            result=result,
            related_results=related_results,
        )

    def is_valid(
        self,
        result: Stage2ScanResult,
        related_results: Iterable[Stage2ScanResult],
    ) -> bool:
        """
        Return True only when every validation stage succeeds.
        """
        validations = self.validate_opportunity(
            result=result,
            related_results=related_results,
        )

        return all(
            validation.valid
            for validation in validations
        )
