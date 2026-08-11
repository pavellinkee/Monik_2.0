"""
Runtime configuration loader.

Supports both:

1. the current normalized flat configuration;
2. the existing nested user configuration.

The user-facing YAML structure is never required to change.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from config.runtime_config import RuntimeConfig


class RuntimeConfigLoader:
    """
    Convert raw configuration into RuntimeConfig.
    """

    def load(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        """
        Load either flat or legacy nested configuration.
        """

        if not isinstance(
            data,
            Mapping,
        ):
            raise TypeError(
                "data must be a mapping."
            )

        if self._is_nested_config(data):
            return self._from_nested_config(
                data
            )

        return self._from_flat_config(
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

    @staticmethod
    def _is_nested_config(
        data: Mapping[str, Any],
    ) -> bool:
        """
        Detect the existing user-facing YAML format.
        """

        return (
            isinstance(
                data.get("stage1"),
                Mapping,
            )
            or isinstance(
                data.get("stage2"),
                Mapping,
            )
            or isinstance(
                data.get("aggregators"),
                Mapping,
            )
        )

    def _from_nested_config(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
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

        if not isinstance(
            stage1,
            Mapping,
        ):
            raise TypeError(
                "stage1 configuration must be a mapping."
            )

        if not isinstance(
            stage2,
            Mapping,
        ):
            raise TypeError(
                "stage2 configuration must be a mapping."
            )

        if not isinstance(
            aggregators,
            Mapping,
        ):
            raise TypeError(
                "aggregators configuration must be a mapping."
            )

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
                "stage1.amount_usdt must be "
                "greater than zero."
            )

        interval_minutes = float(
            stage1.get(
                "base_interval_minutes",
                10.0,
            )
        )

        if interval_minutes <= 0:
            raise ValueError(
                "stage1.base_interval_minutes must "
                "be greater than zero."
            )

        max_interval_minutes = float(
            stage1.get(
                "max_interval_minutes",
                interval_minutes,
            )
        )

        if max_interval_minutes < interval_minutes:
            raise ValueError(
                "stage1.max_interval_minutes cannot "
                "be smaller than base_interval_minutes."
            )

        api_budgets: dict[str, int] = {}

        for name, config in aggregators.items():
            if not isinstance(
                config,
                Mapping,
            ):
                continue

            rate_limit = config.get(
                "rate_limit",
                {},
            )

            if not isinstance(
                rate_limit,
                Mapping,
            ):
                continue

            limit = rate_limit.get(
                "requests_per_minute"
            )

            if limit is not None:
                api_budgets[
                    str(name)
                ] = int(limit)

        return RuntimeConfig(
            enabled_aggregators=(
                enabled_aggregators
            ),
            scan_amounts_usdt=(
                amount,
            ),
            chain_ids=tuple(
                int(chain_id)
                for chain_id
                in data.get(
                    "chain_ids",
                    (),
                )
            ),
            stage1_interval_seconds=(
                interval_minutes * 60.0
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
                stage2.get(
                    "enabled",
                    True,
                )
            ),
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
            api_budget_per_aggregator=(
                api_budgets
            ),
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

    def _from_flat_config(
        self,
        data: Mapping[str, Any],
    ) -> RuntimeConfig:
        enabled_aggregators = tuple(
            str(name)
            for name
            in data.get(
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
            scan_amounts_usdt=(
                amounts
            ),
            chain_ids=tuple(
                int(chain_id)
                for chain_id
                in data.get(
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
