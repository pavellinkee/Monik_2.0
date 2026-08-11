"""
Runtime configuration loader.

Supports both:

1. the existing user-facing ScannerConfig structure;
2. the normalized runtime dictionary structure.

The existing config/user_config.yaml format is preserved.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from config.runtime_config import RuntimeConfig


class RuntimeConfigLoader:
    """
    Converts configuration data into RuntimeConfig.
    """

    def load(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        """
        Normalize either the existing nested configuration
        or the newer flat runtime configuration.
        """

        if not isinstance(
            data,
            Mapping,
        ):
            raise TypeError(
                "data must be a mapping."
            )

        # ---------------------------------------------------------
        # Existing configuration format
        # ---------------------------------------------------------

        stage1 = data.get(
            "stage1",
            {},
        )

        stage2 = data.get(
            "stage2",
            {},
        )

        aggregators = data.get(
            "aggregators",
            {},
        )

        if (
            isinstance(stage1, Mapping)
            and isinstance(stage2, Mapping)
            and isinstance(aggregators, Mapping)
            and (
                "amount_usdt" in stage1
                or "base_interval_minutes" in stage1
            )
        ):
            return self._from_existing_config(
                stage1=stage1,
                stage2=stage2,
                aggregators=aggregators,
                data=data,
            )

        # ---------------------------------------------------------
        # Normalized runtime format
        # ---------------------------------------------------------

        return self._from_runtime_config(
            data
        )

    def from_dict(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        """
        Compatibility alias.
        """

        return self.load(data)

    def _from_existing_config(
        self,
        *,
        stage1: Mapping[str, Any],
        stage2: Mapping[str, Any],
        aggregators: Mapping[str, Any],
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        enabled_aggregators = tuple(
            str(name)
            for name, config
            in aggregators.items()
            if (
                isinstance(
                    config,
                    Mapping,
                )
                and bool(
                    config.get(
                        "enabled",
                        False,
                    )
                )
            )
        )

        amount = Decimal(
            str(
                stage1.get(
                    "amount_usdt",
                    "0",
                )
            )
        )

        if amount <= 0:
            raise ValueError(
                "stage1.amount_usdt must be greater than zero."
            )

        base_interval_minutes = float(
            stage1.get(
                "base_interval_minutes",
                10,
            )
        )

        if base_interval_minutes <= 0:
            raise ValueError(
                "stage1.base_interval_minutes must "
                "be greater than zero."
            )

        stage2_enabled = bool(
            stage2.get(
                "enabled",
                True,
            )
        )

        return RuntimeConfig(
            enabled_aggregators=(
                enabled_aggregators
            ),
            scan_amounts_usdt=(
                amount,
            ),
            chain_ids=tuple(
                int(chain_id)
                for chain_id in data.get(
                    "chain_ids",
                    (),
                )
            ),
            stage1_interval_seconds=(
                base_interval_minutes * 60.0
            ),
            stage1_max_tokens=int(
                data.get(
                    "stage1_max_tokens",
                    30,
                )
            ),
            stage2_enabled=stage2_enabled,
            stage2_max_concurrent_checks=int(
                stage2.get(
                    "max_concurrent_checks",
                    1,
                )
            ),
            stage2_same_aggregator_queue_enabled=bool(
                stage2.get(
                    "same_aggregator_queue_enabled",
                    True,
                )
            ),
            stage2_different_aggregators_parallel=bool(
                stage2.get(
                    "different_aggregators_parallel",
                    True,
                )
            ),
            stage2_priority=bool(
                stage2.get(
                    "priority_over_stage1",
                    True,
                )
            ),
            api_budget_per_aggregator={
                str(name): int(
                    config.get(
                        "rate_limit",
                        {},
                    ).get(
                        "requests_per_minute",
                        0,
                    )
                )
                for name, config
                in aggregators.items()
                if isinstance(
                    config,
                    Mapping,
                )
            },
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

    def _from_runtime_config(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        enabled_aggregators = tuple(
            str(name)
            for name in data.get(
                "enabled_aggregators",
                (),
            )
        )

        amounts = tuple(
            Decimal(str(amount))
            for amount
            in data.get(
                "scan_amounts_usdt",
                (),
            )
        )

        return RuntimeConfig(
            enabled_aggregators=(
                enabled_aggregators
            ),
            scan_amounts_usdt=amounts,
            chain_ids=tuple(
                int(chain)
                for chain in data.get(
                    "chain_ids",
                    (),
                )
            ),
            stage1_interval_seconds=float(
                data.get(
                    "stage1_interval_seconds",
                    600.0,
                )
            ),
            stage1_max_tokens=(
                None
                if data.get(
                    "stage1_max_tokens"
                ) is None
                else int(
                    data.get(
                        "stage1_max_tokens"
                    )
                )
            ),
            stage2_enabled=bool(
                data.get(
                    "stage2_enabled",
                    True,
                )
            ),
            stage2_max_concurrent_checks=int(
                data.get(
                    "stage2_max_concurrent_checks",
                    1,
                )
            ),
            stage2_same_aggregator_queue_enabled=bool(
                data.get(
                    "stage2_same_aggregator_queue_enabled",
                    True,
                )
            ),
            stage2_different_aggregators_parallel=bool(
                data.get(
                    "stage2_different_aggregators_parallel",
                    True,
                )
            ),
            stage2_priority=bool(
                data.get(
                    "stage2_priority",
                    True,
                )
            ),
            api_budget_per_aggregator={
                str(name): int(limit)
                for name, limit
                in data.get(
                    "api_budget_per_aggregator",
                    {},
                ).items()
            },
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
