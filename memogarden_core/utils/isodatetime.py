"""ISO 8601 datetime/date conversion utilities.

This module centralizes all transformations between Python datetime/date objects
and ISO 8601 strings. All date/time operations should use these functions
to ensure consistency and make usage clear across the codebase.
"""

from datetime import datetime, date, UTC


def to_timestamp(dt: datetime) -> str:
    """Convert datetime to ISO 8601 UTC timestamp string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat().replace("+00:00", "Z")


def to_datetime(timestamp: str) -> datetime:
    """Convert ISO 8601 UTC timestamp string to datetime."""
    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


def now() -> str:
    """Get current UTC timestamp as ISO 8601 string."""
    return to_timestamp(datetime.now(UTC))


def to_datestring(d: date) -> str:
    """Convert date to ISO 8601 date string (YYYY-MM-DD)."""
    return d.isoformat()
