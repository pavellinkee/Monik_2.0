"""
Aggregator factory.

Responsibility:
    Creates configured aggregator adapters and puts them
    into an AggregatorRegistry.

Does NOT:
    - store API keys;
    - perform API requests;
    - implement rate limiting;
    - implement request queues;
    - calculate arbitrage;
    - implement Stage 1;
    - implement Stage 2.

Configuration:
    The factory receives configuration data from outside.
    Secrets are never hardcoded here.
"""

from typing import Any

from aggregators.aggregator_interface import AggregatorInterface
from aggregators.http_client import HttpClient
from aggregators.oneinch import OneInchAggregator
from aggregators.registry import AggregatorRegistry
from aggregators.uniswap import UniswapAggregator
from aggregators.velora import VeloraAggregator
from aggregators.zero_x import ZeroXAggregator


class AggregatorFactory:
    """
    Creates configured aggregator adapters.

    Configuration format:

        {
            "1inch": {
                "enabled": True,
                "api_key": "..."
            },
            "0x": {
                "enabled": True,
                "api_key": "..."
            },
            "Uniswap": {
                "enabled": True,
                "api_key": "..."
            },
            "Velora": {
                "enabled": True
            }
        }

    API keys are supplied by the external configuration
    and are never stored in source code.
    """

    _BUILDERS = {
        "1inch": "_build_oneinch",
        "0x": "_build_zero_x",
        "Uniswap": "_build_uniswap",
        "Velora": "_build_velora",
    }

    def __init__(
        self,
        http_client: HttpClient,
    ):
        self._http_client = http_client

    def create(
        self,
        config: dict[str, Any],
    ) -> AggregatorRegistry:
        """
        Create a registry from aggregator configuration.

        Disabled aggregators are skipped.

        Raises:
            TypeError:
                If configuration has an invalid structure.

            ValueError:
                If an enabled aggregator has invalid configuration.
        """
        if not isinstance(config, dict):
            raise TypeError(
                "Aggregator configuration must be a dictionary."
            )

        adapters: list[AggregatorInterface] = []

        for name, aggregator_config in config.items():
            if name not in self._BUILDERS:
                raise ValueError(
                    f"Unknown aggregator: '{name}'."
                )

            if not isinstance(
                aggregator_config,
                dict,
            ):
                raise TypeError(
                    f"Configuration for '{name}' "
                    "must be a dictionary."
                )

            enabled = aggregator_config.get(
                "enabled",
                True,
            )

            if not isinstance(enabled, bool):
                raise TypeError(
                    f"'enabled' for '{name}' "
                    "must be a boolean."
                )

            if not enabled:
                continue

            builder_name = self._BUILDERS[name]

            builder = getattr(
                self,
                builder_name,
            )

            adapter = builder(
                aggregator_config
            )

            adapters.append(adapter)

        return AggregatorRegistry(
            adapters
        )

    def _build_oneinch(
        self,
        config: dict[str, Any],
    ) -> OneInchAggregator:
        """Build the 1inch adapter."""

        api_key = self._get_required_api_key(
            "1inch",
            config,
        )

        return OneInchAggregator(
            http_client=self._http_client,
            api_key=api_key,
        )

    def _build_zero_x(
        self,
        config: dict[str, Any],
    ) -> ZeroXAggregator:
        """Build the 0x adapter."""

        api_key = self._get_required_api_key(
            "0x",
            config,
        )

        return ZeroXAggregator(
            http_client=self._http_client,
            api_key=api_key,
        )

    def _build_uniswap(
        self,
        config: dict[str, Any],
    ) -> UniswapAggregator:
        """Build the Uniswap adapter."""

        api_key = self._get_required_api_key(
            "Uniswap",
            config,
        )

        return UniswapAggregator(
            http_client=self._http_client,
            api_key=api_key,
        )

    def _build_velora(
        self,
        config: dict[str, Any],
    ) -> VeloraAggregator:
        """
        Build the Velora adapter.

        Velora does not require an API key.
        """
        return VeloraAggregator(
            http_client=self._http_client,
        )

    @staticmethod
    def _get_required_api_key(
        aggregator_name: str,
        config: dict[str, Any],
    ) -> str:
        """Return a required API key from configuration."""

        api_key = config.get("api_key")

        if not isinstance(
            api_key,
            str,
        ):
            raise ValueError(
                f"API key is required for "
                f"'{aggregator_name}'."
            )

        api_key = api_key.strip()

        if not api_key:
            raise ValueError(
                f"API key is required for "
                f"'{aggregator_name}'."
            )

        return api_key
