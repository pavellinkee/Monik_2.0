"""
Monik 2.0 entrypoint.

The entrypoint is intentionally thin.

Production infrastructure is assembled separately so that:
    - secrets remain outside source code;
    - tests can inject mocks;
    - VPS configuration can be changed without modifying core;
    - legacy interfaces remain isolated.
"""

from __future__ import annotations

import os
from pathlib import Path

from config.user_config_loader import (
    UserConfigLoader,
)


DEFAULT_CONFIG_PATH = Path(
    os.getenv(
        "MONIK_CONFIG",
        "config/user_config.yaml",
    )
)


def load_runtime_config():
    """
    Load normalized runtime configuration.
    """

    return UserConfigLoader().load_file(
        DEFAULT_CONFIG_PATH
    )


def main() -> None:
    """
    Application entrypoint.

    The actual production dependency graph is completed after
    the integration test phase.
    """

    config = load_runtime_config()

    if not config.enabled_aggregators:
        raise RuntimeError(
            "No aggregators are enabled."
        )

    if not config.chain_ids:
        raise RuntimeError(
            "No chains are configured."
        )

    if not config.scan_amounts_usdt:
        raise RuntimeError(
            "No scan amounts are configured."
        )

    raise RuntimeError(
        "Monik runtime infrastructure is not initialized. "
        "Proceed to integration testing before enabling "
        "production execution."
    )


if __name__ == "__main__":
    main()
