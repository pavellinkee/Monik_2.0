"""
User configuration models.

Responsibility:
    Define and validate all user-editable scanner settings.

Compatibility:
    - preserves the original stage1.amount_usdt interface;
    - preserves the original Stage 1 / Stage 2 configuration;
    - adds multi-amount scanning;
    - adds network selection;
    - adds scanner concurrency controls;
    - adds Telegram notification configuration;
    - adds notification deduplication settings.

This module does not:
    - load YAML;
    - perform HTTP requests;
    - create aggregators;
    - scan;
    - access the database.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

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


class AggregatorConfig(BaseModel):
    """Configuration for one DEX aggregator."""

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
        Original single-amount interface.

    scan_amounts_usdt:
        New multi-amount interface.

    When scan_amounts_usdt is omitted, amount_usdt is used.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    amount_usdt: Decimal = Field(
        gt=0
    )

    scan_amounts_usdt: tuple[
        Decimal,
        ...
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
        "scan_amounts_usdt"
    )
    @classmethod
    def validate_scan_amounts(
        cls,
        value: tuple[
            Decimal,
            ...
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
    def normalize_amounts(
        self,
    ):
        """
        Keep the legacy amount_usdt interface while exposing
        normalized multiple amounts.
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

        if (
            self.max_interval_minutes
            < self.base_interval_minutes
        ):
            raise ValueError(
                "max_interval_minutes cannot be "
                "less than base_interval_minutes."
            )

        return self

    @property
    def amounts_usdt(
        self,
    ) -> tuple[Decimal, ...]:
        """
        Return normalized scan amounts.
        """

        return self.scan_amounts_usdt or (
            self.amount_usdt,
        )

    def validate_intervals(
        self,
    ) -> None:
        """
        Legacy validation interface.
        """

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


class NetworkConfig(BaseModel):
    """
    Blockchain network selection.

    mode:
        auto:
            discover networks from available token addresses.

        whitelist:
            use only chain_ids.

    No network IDs are hardcoded in application code.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    mode: Literal[
        "auto",
        "whitelist",
    ] = "auto"

    chain_ids: tuple[int, ...] = ()

    @field_validator(
        "chain_ids"
    )
    @classmethod
    def validate_chain_ids(
        cls,
        value: tuple[int, ...],
    ):
        for chain_id in value:
            if chain_id <= 0:
                raise ValueError(
                    "chain_ids must contain only "
                    "positive integers."
                )

        return tuple(
            dict.fromkeys(value)
        )

    @model_validator(
        mode="after"
    )
    def validate_mode(
        self,
    ):
        if (
            self.mode == "whitelist"
            and not self.chain_ids
        ):
            raise ValueError(
                "network.chain_ids must not be empty "
                "when network.mode is 'whitelist'."
            )

        return self


class ScannerRuntimeConfig(BaseModel):
    """
    Global scan scheduler limits.

    These settings control scanner-level concurrency.

    Aggregator-specific request concurrency and rate limiting
    remain inside AggregatorRequestQueue.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    max_parallel_chain_amount_jobs: int = Field(
        default=4,
        gt=0,
    )

    stage2_batch_size: int = Field(
        default=1,
        gt=0,
    )

    no_cache: bool = True


class TelegramConfig(BaseModel):
    """Telegram notification configuration."""

    model_config = ConfigDict(
        extra="forbid"
    )

    enabled: bool = False

    bot_token: str | None = None

    chat_id: str | None = None

    timeout_seconds: float = Field(
        default=15.0,
        gt=0,
    )

    send_best_only: bool = True

    include_all_profitable: bool = False

    test_message_enabled: bool = True

    @model_validator(
        mode="after"
    )
    def validate_credentials(
        self,
    ):
        if self.enabled:
            if not self.bot_token:
                raise ValueError(
                    "telegram.bot_token is required "
                    "when Telegram is enabled."
                )

            if not self.chat_id:
                raise ValueError(
                    "telegram.chat_id is required "
                    "when Telegram is enabled."
                )

        return self


class NotificationConfig(BaseModel):
    """Notification selection and deduplication settings."""

    model_config = ConfigDict(
        extra="forbid"
    )

    deduplication_enabled: bool = True

    deduplication_window_seconds: int = Field(
        default=900,
        gt=0,
    )

    best_opportunity_marker: str = "💎"

    minimum_display_profit_usdt: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )


class ScannerConfig(BaseModel):
    """Complete user configuration."""

    model_config = ConfigDict(
        extra="forbid"
    )

    stage1: Stage1Config

    stage2: Stage2Config

    aggregators: dict[
        str,
        AggregatorConfig,
    ]

    network: NetworkConfig = Field(
        default_factory=NetworkConfig
    )

    scanner: ScannerRuntimeConfig = Field(
        default_factory=ScannerRuntimeConfig
    )

    telegram: TelegramConfig = Field(
        default_factory=TelegramConfig
    )

    notifications: NotificationConfig = Field(
        default_factory=NotificationConfig
    )

    def validate(
        self,
    ) -> None:
        """
        Validate cross-section configuration.
        """

        self.stage1.validate_intervals()

        if not self.aggregators:
            raise ValueError(
                "At least one aggregator must be configured."
            )

        enabled_aggregators = tuple(
            name
            for name, config
            in self.aggregators.items()
            if config.enabled
        )

        if not enabled_aggregators:
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

        if (
            self.scanner.max_parallel_chain_amount_jobs
            <= 0
        ):
            raise ValueError(
                "scanner.max_parallel_chain_amount_jobs "
                "must be greater than zero."
            )

        if (
            self.scanner.stage2_batch_size
            <= 0
        ):
            raise ValueError(
                "scanner.stage2_batch_size must "
                "be greater than zero."
            )

    @property
    def enabled_aggregators(
        self,
    ) -> tuple[str, ...]:
        """
        Return enabled aggregator names in configuration order.
        """

        return tuple(
            name
            for name, config
            in self.aggregators.items()
            if config.enabled
        )

    @property
    def scan_amounts_usdt(
        self,
    ) -> tuple[Decimal, ...]:
        """
        Return normalized scan amounts.
        """

        return self.stage1.amounts_usdt
