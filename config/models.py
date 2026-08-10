"""
User configuration models.

Responsibility:
    Defines and validates all user-configurable settings.

Does NOT:
    - load YAML files;
    - make HTTP requests;
    - create aggregators;
    - run Stage 1;
    - run Stage 2;
    - send Telegram messages.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AggregatorRateLimitConfig(BaseModel):
    """Rate-limit settings for one aggregator."""

    model_config = ConfigDict(extra="forbid")

    requests_per_minute: int = Field(
        gt=0,
    )

    initial_delay_seconds: float = Field(
        ge=0,
    )

    adaptive_delay_enabled: bool = True

    delay_multiplier: float = Field(
        gt=1.0,
    )

    max_delay_seconds: float = Field(
        gt=0,
    )

    @field_validator("max_delay_seconds")
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

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    api_key: str | None = None

    rate_limit: AggregatorRateLimitConfig


class Stage1Config(BaseModel):
    """Stage 1 scanning settings."""

    model_config = ConfigDict(extra="forbid")

    amount_usdt: Decimal = Field(
        gt=0,
    )

    base_interval_minutes: int = Field(
        gt=0,
    )

    max_interval_minutes: int = Field(
        gt=0,
    )

    @field_validator("max_interval_minutes")
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

    def validate_intervals(self) -> None:
        """Ensure the maximum interval is not below the base interval."""

        if (
            self.max_interval_minutes
            < self.base_interval_minutes
        ):
            raise ValueError(
                "max_interval_minutes cannot be "
                "less than base_interval_minutes."
            )


class Stage2Config(BaseModel):
    """Stage 2 opportunity verification settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    max_concurrent_checks: int = Field(
        gt=0,
    )

    same_aggregator_queue_enabled: bool = True

    different_aggregators_parallel: bool = True

    priority_over_stage1: bool = True


class ScannerConfig(BaseModel):
    """Global scanner configuration."""

    model_config = ConfigDict(extra="forbid")

    stage1: Stage1Config

    stage2: Stage2Config

    aggregators: dict[
        str,
        AggregatorConfig,
    ]

    def validate(self) -> None:
        """
        Validate cross-section configuration rules.

        These rules cannot be represented by individual fields alone.
        """

        self.stage1.validate_intervals()

        if not self.aggregators:
            raise ValueError(
                "At least one aggregator must be configured."
            )

        enabled_count = sum(
            1
            for config in self.aggregators.values()
            if config.enabled
        )

        if enabled_count == 0:
            raise ValueError(
                "At least one aggregator must be enabled."
            )
