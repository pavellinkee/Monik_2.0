"""
Backward-compatible AggregatorEngine import.

The canonical implementation lives in:
    core.aggregator_engine

This module keeps the previous import path working for
existing callers and tests.
"""

from core.aggregator_engine import (
    AggregatorEngine,
)

__all__ = [
    "AggregatorEngine",
]
