"""
Normalized runtime configuration.

This model is an internal representation of the existing
ScannerConfig.

Important:
    The user-facing YAML format remains unchanged.

The runtime layer may additionally receive chain_ids from the
token/database layer. They are therefore optional here.

Compatibility:
    - preserves the existing ScannerConfig structure;
    - supports the newer normalized runtime representation;
    - does not require users to rewrite user_config.yaml.
"""

from __future__ import annotations

from decimal import Decimal

from models.base_model import BaseModel


class RuntimeConfig(BaseModel):
    """
    Normalized configuration used by runtime components.
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

    api_budget_per_aggregator: dict[str, int] = {}

    stage2_reserved_api_capacity: int = 0

    telegram_enabled: bool = False

    telegram_bot_token: str | None = None

    telegram_chat_id: str | None = None

    @property
    def amount_usdt(self) -> Decimal:
        """
        Legacy single-amount interface.

        Returns the first configured scan amount.
        """

        return self.scan_amounts_usdt[0]

    @property
    def stage1_interval_minutes(self) -> float:
        """
        Compatibility helper for the user configuration model.
        """

        return self.stage1_interval_seconds / 60.0

    @property
    def aggregators(self) -> tuple[str, ...]:
        """
        Compatibility alias.
        """

        return self.enabled_aggregators

    def has_chain_configuration(self) -> bool:
        """
        Return True when explicit chain IDs are configured.
        """

        return bool(self.chain_ids)
