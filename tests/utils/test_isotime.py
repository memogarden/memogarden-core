"""Tests for isotime module."""

import pytest
from datetime import datetime, UTC, timedelta
from memogarden_core.utils import isotime


class TestToTimestamp:
    """Tests for to_timestamp function."""

    def test_converts_naive_datetime_to_utc(self):
        """Naive datetime should be treated as UTC."""
        dt = datetime(2025, 12, 23, 10, 30, 0)
        result = isotime.to_timestamp(dt)
        assert result == "2025-12-23T10:30:00Z"

    def test_converts_aware_datetime_to_utc(self):
        """Aware datetime should preserve UTC."""
        dt = datetime(2025, 12, 23, 10, 30, 0, tzinfo=UTC)
        result = isotime.to_timestamp(dt)
        assert result == "2025-12-23T10:30:00Z"

    def test_handles_microseconds(self):
        """Should preserve microseconds in ISO format."""
        dt = datetime(2025, 12, 23, 10, 30, 0, 123456, tzinfo=UTC)
        result = isotime.to_timestamp(dt)
        assert result == "2025-12-23T10:30:00.123456Z"


class TestToDatetime:
    """Tests for to_datetime function."""

    def test_converts_z_suffix(self):
        """Should parse timestamp with Z suffix."""
        timestamp = "2025-12-23T10:30:00Z"
        result = isotime.to_datetime(timestamp)
        assert result == datetime(2025, 12, 23, 10, 30, 0, tzinfo=UTC)

    def test_converts_with_microseconds(self):
        """Should parse timestamp with microseconds."""
        timestamp = "2025-12-23T10:30:00.123456Z"
        result = isotime.to_datetime(timestamp)
        assert result == datetime(2025, 12, 23, 10, 30, 0, 123456, tzinfo=UTC)


class TestNow:
    """Tests for now function."""

    def test_returns_valid_iso8601_format(self):
        """Should return valid ISO 8601 timestamp."""
        result = isotime.now()
        assert isinstance(result, str)
        assert result.endswith("Z")
        # Should be parseable
        parsed = isotime.to_datetime(result)
        assert isinstance(parsed, datetime)

    def test_returns_recent_timestamp(self):
        """Should return timestamp within last second."""
        before = datetime.now(UTC)
        result = isotime.now()
        after = datetime.now(UTC)

        parsed = isotime.to_datetime(result)
        assert before <= parsed <= after


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_datetime_to_timestamp_to_datetime(self):
        """Should preserve datetime through round-trip."""
        original = datetime(2025, 12, 23, 10, 30, 0, tzinfo=UTC)
        timestamp = isotime.to_timestamp(original)
        result = isotime.to_datetime(timestamp)
        assert result == original

    def test_naive_datetime_round_trip(self):
        """Naive datetime should become UTC-aware after round-trip."""
        original = datetime(2025, 12, 23, 10, 30, 0)
        timestamp = isotime.to_timestamp(original)
        result = isotime.to_datetime(timestamp)
        assert result.tzinfo == UTC
        # Time should be preserved
        assert result.hour == 10
        assert result.minute == 30
