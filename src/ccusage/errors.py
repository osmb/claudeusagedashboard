"""Domain-specific exception types."""


class CcusageError(Exception):
    """Base exception for all ccusage errors."""


class CollectorError(CcusageError):
    """Raised when the ccusage CLI call fails or returns unexpected data."""


class HistoryImportError(CcusageError):
    """Raised when a historical data import fails."""
