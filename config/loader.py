"""
YAML configuration loader.

Responsibility:
    Loads YAML data from a file and converts it into
    a validated ScannerConfig.

Does NOT:
    - create aggregators;
    - make HTTP requests;
    - run Stage 1;
    - run Stage 2;
    - send Telegram messages;
    - contain configuration values itself.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from config.models import ScannerConfig


class ConfigLoadError(Exception):
    """Raised when user configuration cannot be loaded."""


class ConfigLoader:
    """Loads and validates the user configuration."""

    def load(
        self,
        path: str | Path,
    ) -> ScannerConfig:
        """
        Load configuration from a YAML file.

        Args:
            path:
                Path to the YAML configuration file.

        Returns:
            Validated ScannerConfig.

        Raises:
            ConfigLoadError:
                If the file cannot be read, parsed,
                or validated.
        """

        config_path = Path(path)

        if not config_path.exists():
            raise ConfigLoadError(
                f"Configuration file does not exist: "
                f"{config_path}"
            )

        if not config_path.is_file():
            raise ConfigLoadError(
                f"Configuration path is not a file: "
                f"{config_path}"
            )

        try:
            with config_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                raw_data = yaml.safe_load(file)

        except OSError as error:
            raise ConfigLoadError(
                f"Could not read configuration file: "
                f"{config_path}"
            ) from error

        except yaml.YAMLError as error:
            raise ConfigLoadError(
                f"Invalid YAML syntax in configuration file: "
                f"{config_path}"
            ) from error

        if raw_data is None:
            raise ConfigLoadError(
                "Configuration file is empty."
            )

        if not isinstance(raw_data, dict):
            raise ConfigLoadError(
                "Configuration root must be a YAML mapping."
            )

        try:
            config = ScannerConfig(
                **raw_data
            )

            config.validate()

        except ValidationError as error:
            raise ConfigLoadError(
                "Configuration validation failed."
            ) from error

        except ValueError as error:
            raise ConfigLoadError(
                "Configuration validation failed."
            ) from error

        return config
