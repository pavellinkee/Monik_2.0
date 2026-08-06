"""
Project exceptions.

Responsibility:
    Defines the common exception hierarchy used by the entire project.

All project-specific exceptions must inherit from ScannerError.
"""


class ScannerError(Exception):
    """Base exception for the project."""


class ConfigurationError(ScannerError):
    """Configuration is invalid."""


class ValidationError(ScannerError):
    """Validation failed."""


class AggregatorError(ScannerError):
    """Aggregator request or response error."""


class TokenError(ScannerError):
    """Token system error."""


class DatabaseError(ScannerError):
    """Database operation failed."""


class NetworkError(ScannerError):
    """Network communication failed."""


class HealthCheckError(ScannerError):
    """Health monitor detected a failure."""
