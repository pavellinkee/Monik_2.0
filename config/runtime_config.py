"""
Runtime configuration models.

Responsibility:
    Represent normalized runtime configuration used by the
    application.

The runtime layer must not depend directly on YAML structure.
"""

from __future__ import annotations

from decimal import Decimal

from models.base_model import BaseModel


class RuntimeConfig(BaseModel):
    """
    Normalized application configuration.
    """

    enabled_aggregators: tuple[str, ...]

    chain_ids: tuple[int, ...]

    scan_amounts_usdt: tuple[Decimal, ...]

    stage1_interval_seconds: float = 600.0

    stage2_max_concurrent_checks: int = 1

    stage2_priority: bool = True

    api_budget_per_aggregator: dict[
        str,
        int,
    ] = {}

    stage2_reserved_api_capacity: int = 0

    telegram_enabled: bool = False

    telegram_bot_token: str | None = None

    telegram_chat_id: str | None = None
