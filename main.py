"""
Monik 2.0 production entrypoint.

The entrypoint is intentionally thin.

Business logic belongs to core modules.
"""

from __future__ import annotations

import asyncio
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


def main() -> None:
    """
    Start the Monik scanner.
    """

    config = UserConfigLoader().load_file(
        DEFAULT_CONFIG_PATH
    )

    # The final infrastructure wiring is intentionally delegated
    # to the application factory.
    #
    # ScannerEngine, AggregatorEngine, database and real
    # aggregator implementations are connected here after the
    # complete codebase has passed the integration test phase.

    _ = config

    raise RuntimeError(
        "Production dependency wiring is not initialized yet. "
        "Run the integration setup phase before starting Monik."
    )


if __name__ == "__main__":
    main()
