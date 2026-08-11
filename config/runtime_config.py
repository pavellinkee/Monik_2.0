"""
Normalized runtime configuration.

The user-facing YAML format is intentionally kept separate from
this internal runtime representation.

Compatibility:
    - current normalized configuration;
    - legacy ScannerConfig-style configuration;
    - single scan amount;
    - multiple scan amounts.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from models.base_model import BaseModel


class RuntimeConfig(BaseModel):
    """
    Immutable normalized runtime configuration.
    """

    enabled_aggregators: tuple[str, ...]

    scan_amounts_usdt: tuple[Decimal, ...]

    chain_ids: tuple[int, ...] = ()

    stage1_interval_seconds: float = 600.0

    stage1_max_tokens: int | None = 30

    stage2_enabled: bool = True

    stage2_max_concurrent_checks: int = 1

    stage2_same_aggregator_queue_enabled: bool = True

    stage2_different_aggregators_parallel: bool = True

    stage2_priority: bool = True

    api_budget_per_aggregator: dict[str, int] = Field(
        default_factory=dict
    )

    stage2_reserved_api_capacity: int = 0

    telegram_enabled: bool = False

    telegram_bot_token: str | None = None

    telegram_chat_id: str | None = None

    @property
    def amount_usdt(self) -> Decimal:
        """
        Legacy single-amount interface.
        """

        if not self.scan_amounts_usdt:
            raise ValueError(
                "No scan amounts are configured."
            )

        return self.scan_amounts_usdt[0]

    @property
    def stage1_interval_minutes(self) -> float:
        """
        Return Stage 1 interval in minutes.
        """

        return (
            self.stage1_interval_seconds / 60.0
        )

    @property
    def aggregators(self) -> tuple[str, ...]:
        """
        Legacy alias for enabled aggregators.
        """

        return self.enabled_aggregators

    def has_chain_configuration(self) -> bool:
        """
        Return True when chains are explicitly configured.
        """

        return bool(self.chain_ids)
