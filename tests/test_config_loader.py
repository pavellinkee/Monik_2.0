"""
Tests for ConfigLoader.
"""

from pathlib import Path

import pytest
import yaml

from config.loader import (
    ConfigLoadError,
    ConfigLoader,
)


def create_valid_config() -> dict:
    """Return a valid configuration dictionary."""

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
                "rate_limit": {
                    "requests_per_minute": 60,
                    "initial_delay_seconds": 1.0,
                    "adaptive_delay_enabled": True,
                    "delay_multiplier": 1.5,
                    "max_delay_seconds": 10.0,
                },
            },
            "Velora": {
                "enabled": True,
                "api_key": None,
                "rate_limit": {
                    "requests_per_minute": 60,
                    "initial_delay_seconds": 1.0,
                    "adaptive_delay_enabled": True,
                    "delay_multiplier": 1.5,
                    "max_delay_seconds": 10.0,
                },
            },
        },
    }


def write_yaml(
    path: Path,
    data: dict,
) -> None:
    """Write test configuration to YAML."""

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


def test_loader_reads_valid_yaml(
    tmp_path,
):
    """Valid YAML is converted into ScannerConfig."""

    path = tmp_path / "config.yaml"

    write_yaml(
        path,
        create_valid_config(),
    )

    config = ConfigLoader().load(path)

    assert config.stage1.amount_usdt == 1000
    assert (
        config.stage1.base_interval_minutes
        == 10
    )

    assert (
        config.stage1.max_interval_minutes
        == 30
    )

    assert config.stage2.enabled is True

    assert "1inch" in config.aggregators
    assert "Velora" in config.aggregators


def test_loader_preserves_api_keys(
    tmp_path,
):
    """API keys are loaded without modification."""

    path = tmp_path / "config.yaml"

    data = create_valid_config()

    write_yaml(
        path,
        data,
    )

    config = ConfigLoader().load(path)

    assert (
        config.aggregators["1inch"].api_key
        == "test-1inch-key"
    )

    assert (
        config.aggregators["Velora"].api_key
        is None
    )


def test_loader_rejects_missing_file(
    tmp_path,
):
    """Missing configuration files are rejected."""

    path = tmp_path / "missing.yaml"

    with pytest.raises(ConfigLoadError):
        ConfigLoader().load(path)


def test_loader_rejects_empty_file(
    tmp_path,
):
    """Empty YAML files are rejected."""

    path = tmp_path / "empty.yaml"

    path.write_text(
        "",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError):
        ConfigLoader().load(path)


def test_loader_rejects_invalid_yaml(
    tmp_path,
):
    """Invalid YAML syntax is rejected."""

    path = tmp_path / "invalid.yaml"

    path.write_text(
        "stage1: [invalid",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError):
        ConfigLoader().load(path)


def test_loader_rejects_non_mapping_root(
    tmp_path,
):
    """The YAML root must be a mapping."""

    path = tmp_path / "invalid.yaml"

    path.write_text(
        "- one\n- two\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError):
        ConfigLoader().load(path)


def test_loader_rejects_invalid_configuration(
    tmp_path,
):
    """Invalid configuration values are rejected."""

    path = tmp_path / "invalid.yaml"

    data = create_valid_config()

    data["stage1"]["amount_usdt"] = 0

    write_yaml(
        path,
        data,
    )

    with pytest.raises(ConfigLoadError):
        ConfigLoader().load(path)


def test_loader_rejects_unknown_configuration_fields(
    tmp_path,
):
    """Unknown fields are rejected by Pydantic."""

    path = tmp_path / "invalid.yaml"

    data = create_valid_config()

    data["stage1"]["unknown_setting"] = True

    write_yaml(
        path,
        data,
    )

    with pytest.raises(ConfigLoadError):
        ConfigLoader().load(path)
