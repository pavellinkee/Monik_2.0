"""
Common project enumerations.

Responsibility:
    Defines shared enums used across the project.

Does NOT:
    - contain business logic;
    - communicate with external services;
    - perform calculations.
"""

from enum import Enum


class ApplyMode(str, Enum):
    """Configuration apply mode."""

    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


class Severity(str, Enum):
    """Diagnostic severity."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class HealthStatus(str, Enum):
    """Health check result."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class AggregatorStatus(str, Enum):
    """Aggregator availability."""

    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class SourceType(str, Enum):
    """External data source priority."""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


class UpdateResult(str, Enum):
    """Update operation result."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AlertType(str, Enum):
    """Alert categories."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    RECOVERY = "RECOVERY"


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"
