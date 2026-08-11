"""
Runtime configuration loader.

Responsibility:
    Convert configuration data into RuntimeConfig.

The loader supports dictionary input so tests and production
configuration can use the same normalized interface.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from config.runtime_config import (
    RuntimeConfig,
)


class RuntimeConfigLoader:
    """
    Converts raw configuration dictionaries into RuntimeConfig.
    """

    def load(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        """
        Normalize raw configuration.
        """

        if not isinstance(
            data,
            Mapping,
        ):
            raise TypeError(
                "data must be a mapping."
            )

        aggregators = tuple(
            str(name)
            for name in data.get(
                "enabled_aggregators",
                (),
            )
        )

        chains = tuple(
            int(chain)
            for chain in data.get(
                "chain_ids",
                (),
            )
        )

        amounts = tuple(
            Decimal(str(amount))
            for amount in data.get(
                "scan_amounts_usdt",
                (),
            )
        )

        budgets = {
            str(name): int(limit)
            for name, limit in data.get(
                "api_budget_per_aggregator",
                {},
            ).items()
        }

        return RuntimeConfig(
            enabled_aggregators=aggregators,
            chain_ids=chains,
            scan_amounts_usdt=amounts,
            stage1_interval_seconds=float(
                data.get(
                    "stage1_interval_seconds",
                    600.0,
                )
            ),
            stage2_max_concurrent_checks=int(
                data.get(
                    "stage2_max_concurrent_checks",
                    1,
                )
            ),
            stage2_priority=bool(
                data.get(
                    "stage2_priority",
                    True,
                )
            ),
            api_budget_per_aggregator=budgets,
            stage2_reserved_api_capacity=int(
                data.get(
                    "stage2_reserved_api_capacity",
                    0,
                )
            ),
            telegram_enabled=bool(
                data.get(
                    "telegram_enabled",
                    False,
                )
            ),
            telegram_bot_token=data.get(
                "telegram_bot_token"
            ),
            telegram_chat_id=data.get(
                "telegram_chat_id"
            ),
        )

    def from_dict(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        """
        Compatibility alias.
        """

        return self.load(data)
