"""
User configuration loader.

The existing ConfigLoader remains the authoritative validator for
the user-facing YAML format.

Flow:

    YAML
      ↓
    ConfigLoader
      ↓
    ScannerConfig
      ↓
    RuntimeConfigLoader
      ↓
    RuntimeConfig

This prevents two different validation rules from existing for
the same user configuration.
"""

from __future__ import annotations

from pathlib import Path

from config.loader import (
    ConfigLoader,
)
from config.models import (
    ScannerConfig,
)
from config.runtime_config import (
    RuntimeConfig,
)
from config.runtime_config_loader import (
    RuntimeConfigLoader,
)


class UserConfigLoader:
    """
    Load and validate the user-facing YAML configuration.
    """

    def __init__(
        self,
        config_loader: ConfigLoader | None = None,
        runtime_loader: RuntimeConfigLoader | None = None,
    ) -> None:
        self._config_loader = (
            config_loader
            or ConfigLoader()
        )

        self._runtime_loader = (
            runtime_loader
            or RuntimeConfigLoader()
        )

    def load_file(
        self,
        path: str | Path,
    ) -> RuntimeConfig:
        """
        Load the user configuration through the authoritative
        ScannerConfig validation pipeline.
        """

        config = self._config_loader.load(
            path
        )

        if not isinstance(
            config,
            ScannerConfig,
        ):
            raise TypeError(
                "ConfigLoader must return ScannerConfig."
            )

        return self._runtime_loader.load(
            config
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
