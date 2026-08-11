"""
User configuration models.

Responsibility:
    Defines and validates all user-configurable settings.

Compatibility:
    - legacy single amount: amount_usdt
    - new multiple amounts: scan_amounts_usdt

The legacy interface remains valid.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class AggregatorRateLimitConfig(BaseModel):
    """Rate-limit settings for one aggregator."""

    model_config = ConfigDict(
        extra="forbid"
    )

    requests_per_minute: int = Field(
        gt=0
    )

    initial_delay_seconds: float = Field(
        ge=0
    )

    adaptive_delay_enabled: bool = True

    delay_multiplier: float = Field(
        gt=1.0
    )

    max_delay_seconds: float = Field(
        gt=0
    )

    @field_validator(
        "max_delay_seconds"
    )
    @classmethod
    def validate_max_delay(
        cls,
        value: float,
    ) -> float:
        if value <= 0:
            raise ValueError(
                "max_delay_seconds must be greater than 0."
            )

        return value


class AggregatorConfig(BaseModel):
    """Configuration for one aggregator."""

    model_config = ConfigDict(
        extra="forbid"
    )

    enabled: bool = True

    api_key: str | None = None

    rate_limit: AggregatorRateLimitConfig


class Stage1Config(BaseModel):
    """
    Stage 1 scanning settings.

    amount_usdt:
        Legacy single scan amount.

    scan_amounts_usdt:
        Preferred multi-amount interface.

    When only amount_usdt is provided, it is automatically converted
    into a one-item scan_amounts_usdt tuple.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    amount_usdt: Decimal = Field(
        gt=0
    )

    scan_amounts_usdt: tuple[
        Decimal,
        ...,
    ] | None = None

    base_interval_minutes: int = Field(
        gt=0
    )

    max_interval_minutes: int = Field(
        gt=0
    )

    max_tokens: int = Field(
        default=30,
        gt=0,
    )

    @field_validator(
        "max_interval_minutes"
    )
    @classmethod
    def validate_max_interval(
        cls,
        value: int,
    ) -> int:
        if value <= 0:
            raise ValueError(
                "max_interval_minutes must be greater than 0."
            )

        return value

    @field_validator(
        "scan_amounts_usdt"
    )
    @classmethod
    def validate_scan_amounts(
        cls,
        value: tuple[
            Decimal,
            ...,
        ]
        | None,
    ):
        if value is None:
            return value

        if not value:
            raise ValueError(
                "scan_amounts_usdt cannot be empty."
            )

        for amount in value:
            if amount <= Decimal("0"):
                raise ValueError(
                    "All scan amounts must be greater than zero."
                )

        return value

    @model_validator(
        mode="after"
    )
    def normalize_scan_amounts(
        self,
    ):
        """
        Preserve the legacy amount_usdt interface while creating
        the normalized multi-amount representation.
        """

        if self.scan_amounts_usdt is None:
            object.__setattr__(
                self,
                "scan_amounts_usdt",
                (
                    self.amount_usdt,
                ),
            )

        else:
            object.__setattr__(
                self,
                "amount_usdt",
                self.scan_amounts_usdt[0],
            )

        return self

    def validate_intervals(
        self,
    ) -> None:
        """
        Ensure maximum interval is not below base interval.
        """

        if (
            self.max_interval_minutes
            < self.base_interval_minutes
        ):
            raise ValueError(
                "max_interval_minutes cannot be "
                "less than base_interval_minutes."
            )

    @property
    def amounts_usdt(
        self,
    ) -> tuple[Decimal, ...]:
        """
        Preferred normalized multi-amount interface.
        """

        return self.scan_amounts_usdt or (
            self.amount_usdt,
        )


class Stage2Config(BaseModel):
    """Stage 2 opportunity verification settings."""

    model_config = ConfigDict(
        extra="forbid"
    )

    enabled: bool = True

    max_concurrent_checks: int = Field(
        gt=0
    )

    same_aggregator_queue_enabled: bool = True

    different_aggregators_parallel: bool = True

    priority_over_stage1: bool = True


class ScannerConfig(BaseModel):
    """Global scanner configuration."""

    model_config = ConfigDict(
        extra="forbid"
    )

    stage1: Stage1Config

    stage2: Stage2Config

    aggregators: dict[
        str,
        AggregatorConfig,
    ]

    def validate(
        self,
    ) -> None:
        """
        Validate cross-section configuration rules.
        """

        self.stage1.validate_intervals()

        if not self.aggregators:
            raise ValueError(
                "At least one aggregator must be configured."
            )

        enabled_count = sum(
            1
            for config
            in self.aggregators.values()
            if config.enabled
        )

        if enabled_count == 0:
            raise ValueError(
                "At least one aggregator must be enabled."
            )

        if (
            self.stage2.max_concurrent_checks
            <= 0
        ):
            raise ValueError(
                "stage2.max_concurrent_checks must "
                "be greater than zero."
            )
