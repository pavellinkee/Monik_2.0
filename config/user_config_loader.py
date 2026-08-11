"""
User configuration loader.

Loads the user-editable YAML file and delegates normalization
to RuntimeConfigLoader.
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
    Load user-facing YAML configuration.
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
        Load and normalize one YAML configuration file.
        """

        config_path = Path(
            path
        )

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
            raw: Any = yaml.safe_load(
                file
            )

        if raw is None:
            raw = {}

        if not isinstance(
            raw,
            dict,
        ):
            raise TypeError(
                "Root configuration must be a mapping."
            )

        return self._runtime_loader.load(
            raw
        )

    def load(
        self,
        path: str | Path,
    ) -> RuntimeConfig:
        """
        Compatibility alias.
        """

        return self.load_file(
            path
        )
