"""
User configuration loader.

Responsibility:
    Load user configuration from YAML and normalize it into the
    runtime configuration layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config.runtime_config import RuntimeConfig
from config.runtime_config_loader import (
    RuntimeConfigLoader,
)


class UserConfigLoader:
    """
    Loads the user's YAML configuration.
    """

    def __init__(
        self,
        runtime_loader: RuntimeConfigLoader | None = None,
    ) -> None:
        self._runtime_loader = (
            runtime_loader
            or RuntimeConfigLoader()
        )

    def load_file(
        self,
        path: str | Path,
    ) -> RuntimeConfig:
        """
        Load a YAML configuration file.
        """

        config_path = Path(path)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: "
                f"{config_path}"
            )

        if not config_path.is_file():
            raise ValueError(
                f"Configuration path is not a file: "
                f"{config_path}"
            )

        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required to load "
                "user configuration."
            ) from exc

        with config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            raw: Any = yaml.safe_load(file)

        if raw is None:
            raw = {}

        if not isinstance(
            raw,
            dict,
        ):
            raise TypeError(
                "Root configuration must be a mapping."
            )

        normalized = self._normalize(
            raw
        )

        return self._runtime_loader.load(
            normalized
        )

    def load(
        self,
        path: str | Path,
    ) -> RuntimeConfig:
        """
        Compatibility alias for load_file().
        """
        return self.load_file(path)

    @staticmethod
    def _normalize(
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract runtime configuration from either the new flat
        structure or the previously used nested structure.
        """

        result = dict(raw)

        scanner = raw.get(
            "scanner",
            {},
        )

        if isinstance(
            scanner,
            dict,
        ):
            result.setdefault(
                "stage1_interval_seconds",
                scanner.get(
                    "stage1_interval_seconds"
                ),
            )

            result.setdefault(
                "stage2_max_concurrent_checks",
                scanner.get(
                    "stage2_max_concurrent_checks"
                ),
            )

            result.setdefault(
                "stage2_priority",
                scanner.get(
                    "stage2_priority"
                ),
            )

        aggregators = raw.get(
            "aggregators",
            {},
        )

        if isinstance(
            aggregators,
            dict,
        ):
            enabled = tuple(
                name
                for name, value
                in aggregators.items()
                if (
                    isinstance(
                        value,
                        dict,
                    )
                    and value.get(
                        "enabled",
                        False,
                    )
                )
            )

            if enabled:
                result.setdefault(
                    "enabled_aggregators",
                    enabled,
                )

        return {
            key: value
            for key, value
            in result.items()
            if value is not None
        }
