"""ISO 8601 timestamp/datetime conversion utilities.

This module centralizes all transformations between Python datetime objects
and ISO 8601 timestamp strings. All timestamp operations should use these
functions to ensure consistency.
"""

from datetime import datetime, UTC


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
