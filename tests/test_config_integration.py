"""
Integration tests for the configuration block.

Tests the complete configuration flow:

    YAML
      ↓
    ConfigLoader
      ↓
    ScannerConfig
      ↓
    AggregatorFactory
      ↓
    AggregatorRegistry
      ↓
    Aggregator adapters

These tests do not contact real APIs.
"""

from pathlib import Path

import pytest
import yaml

from aggregators.factory import AggregatorFactory
from aggregators.http_client import HttpClient
from config.loader import ConfigLoader
from config.models import ScannerConfig


def create_valid_config() -> dict:
    """Return a complete valid user configuration."""

    rate_limit = {
        "requests_per_minute": 50,
        "initial_delay_seconds": 1.2,
        "adaptive_delay_enabled": True,
        "delay_multiplier": 1.5,
        "max_delay_seconds": 30.0,
    }

    return {
        "stage1": {
            "amount_usdt": 1000,
            "base_interval_minutes": 10,
            "max_interval_minutes": 30,
        },
        "stage2": {
            "enabled": True,
            "max_concurrent_checks": 1,
            "same_aggregator_queue_enabled": True,
            "different_aggregators_parallel": True,
            "priority_over_stage1": True,
        },
        "aggregators": {
            "1inch": {
                "enabled": True,
                "api_key": "test-1inch-key",
                "rate_limit": rate_limit.copy(),
            },
            "0x": {
                "enabled": True,
                "api_key": "test-0x-key",
                "rate_limit": rate_limit.copy(),
            },
            "Uniswap": {
                "enabled": True,
                "api_key": "test-uniswap-key",
                "rate_limit": rate_limit.copy(),
            },
            "Velora": {
                "enabled": True,
                "api_key": None,
                "rate_limit": rate_limit.copy(),
            },
        },
    }


def write_yaml(
    path: Path,
    data: dict,
) -> None:
    """Write configuration data to YAML."""

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        yaml.safe_dump(
            data,
            file,
            allow_unicode=True,
            sort_keys=False,
        )


class FakeHttpClient:
    """Fake HTTP client for integration tests."""

    async def get(
        self,
        url,
        *,
        headers=None,
        params=None,
    ):
        """Return a fake successful GET response."""

        return 200, {}

    async def post(
        self,
        url,
        *,
        headers=None,
        json=None,
        params=None,
    ):
        """Return a fake successful POST response."""

        return 200, {}


def test_full_configuration_pipeline(
    tmp_path,
):
    """
    Test the complete configuration pipeline.

    YAML → Loader → ScannerConfig → Factory → Registry
    """

    path = tmp_path / "user_config.yaml"

    write_yaml(
        path,
        create_valid_config(),
    )

    loader = ConfigLoader()

    config = loader.load(path)

    assert isinstance(
        config,
        ScannerConfig,
    )

    assert (
        config.stage1.amount_usdt == 1000
    )

    assert (
        config.stage1.base_interval_minutes
        == 10
    )

    assert (
        config.stage1.max_interval_minutes
        == 30
    )

    assert (
        config.stage2.priority_over_stage1
        is True
    )

    http_client = FakeHttpClient()

    factory = AggregatorFactory(
        http_client=http_client
    )

    registry = factory.create(
        config.aggregators
    )

    assert len(registry) == 4

    assert registry.contains("1inch")
    assert registry.contains("0x")
    assert registry.contains("Uniswap")
    assert registry.contains("Velora")


def test_disabled_aggregator_stays_disabled(
    tmp_path,
):
    """Disabled aggregators remain absent from the registry."""

    path = tmp_path / "user_config.yaml"

    data = create_valid_config()

    data["aggregators"]["1inch"]["enabled"] = False

    write_yaml(
        path,
        data,
    )

    config = ConfigLoader().load(path)

    factory = AggregatorFactory(
        http_client=FakeHttpClient()
    )

    registry = factory.create(
        config.aggregators
    )

    assert len(registry) == 3

    assert not registry.contains("1inch")
    assert registry.contains("0x")
    assert registry.contains("Uniswap")
    assert registry.contains("Velora")


def test_user_can_change_stage1_amount(
    tmp_path,
):
    """
    Stage 1 amount comes from user configuration.

    This confirms that 1000 USDT is not hardcoded.
    """

    path = tmp_path / "user_config.yaml"

    data = create_valid_config()

    data["stage1"]["amount_usdt"] = 500

    write_yaml(
        path,
        data,
    )

    config = ConfigLoader().load(path)

    assert config.stage1.amount_usdt == 500


def test_user_can_change_stage1_interval(
    tmp_path,
):
    """Stage 1 interval is controlled by configuration."""

    path = tmp_path / "user_config.yaml"

    data = create_valid_config()

    data["stage1"]["base_interval_minutes"] = 15
    data["stage1"]["max_interval_minutes"] = 30

    write_yaml(
        path,
        data,
    )

    config = ConfigLoader().load(path)

    assert (
        config.stage1.base_interval_minutes
        == 15
    )

    assert (
        config.stage1.max_interval_minutes
        == 30
    )


def test_velora_works_without_api_key(
    tmp_path,
):
    """Velora can be configured without an API key."""

    path = tmp_path / "user_config.yaml"

    data = create_valid_config()

    data["aggregators"]["1inch"]["enabled"] = False
    data["aggregators"]["0x"]["enabled"] = False
    data["aggregators"]["Uniswap"]["enabled"] = False

    write_yaml(
        path,
        data,
    )

    config = ConfigLoader().load(path)

    factory = AggregatorFactory(
        http_client=FakeHttpClient()
    )

    registry = factory.create(
        config.aggregators
    )

    assert len(registry) == 1

    assert registry.contains("Velora")

    assert (
        registry.get("Velora").name
        == "Velora"
    )


def test_stage2_priority_is_preserved(
    tmp_path,
):
    """Stage 2 priority survives the YAML pipeline."""

    path = tmp_path / "user_config.yaml"

    data = create_valid_config()

    write_yaml(
        path,
        data,
    )

    config = ConfigLoader().load(path)

    assert (
        config.stage2.priority_over_stage1
        is True
    )

    assert (
        config.stage2
        .same_aggregator_queue_enabled
        is True
    )

    assert (
        config.stage2
        .different_aggregators_parallel
        is True
    )
