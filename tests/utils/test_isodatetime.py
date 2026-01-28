"""Tests for isodatetime module."""

import pytest
from datetime import datetime, date, UTC, timedelta
from memogarden.utils import isodatetime


class TestToTimestamp:
    """Tests for to_timestamp function."""

    def test_converts_naive_datetime_to_utc(self):
        """Naive datetime should be treated as UTC."""
        dt = datetime(2025, 12, 23, 10, 30, 0)
        result = isodatetime.to_timestamp(dt)
        assert result == "2025-12-23T10:30:00Z"

    def test_converts_aware_datetime_to_utc(self):
        """Aware datetime should preserve UTC."""
        dt = datetime(2025, 12, 23, 10, 30, 0, tzinfo=UTC)
        result = isodatetime.to_timestamp(dt)
        assert result == "2025-12-23T10:30:00Z"

    def test_handles_microseconds(self):
        """Should preserve microseconds in ISO format."""
        dt = datetime(2025, 12, 23, 10, 30, 0, 123456, tzinfo=UTC)
        result = isodatetime.to_timestamp(dt)
        assert result == "2025-12-23T10:30:00.123456Z"


class TestToDatetime:
    """Tests for to_datetime function."""

    def test_converts_z_suffix(self):
        """Should parse timestamp with Z suffix."""
        timestamp = "2025-12-23T10:30:00Z"
        result = isodatetime.to_datetime(timestamp)
        assert result == datetime(2025, 12, 23, 10, 30, 0, tzinfo=UTC)

    def test_converts_with_microseconds(self):
        """Should parse timestamp with microseconds."""
        timestamp = "2025-12-23T10:30:00.123456Z"
        result = isodatetime.to_datetime(timestamp)
        assert result == datetime(2025, 12, 23, 10, 30, 0, 123456, tzinfo=UTC)


class TestNow:
    """Tests for now function."""

    def test_returns_valid_iso8601_format(self):
        """Should return valid ISO 8601 timestamp."""
        result = isodatetime.now()
        assert isinstance(result, str)
        assert result.endswith("Z")
        # Should be parseable
        parsed = isodatetime.to_datetime(result)
        assert isinstance(parsed, datetime)

    def test_returns_recent_timestamp(self):
        """Should return timestamp within last second."""
        before = datetime.now(UTC)
        result = isodatetime.now()
        after = datetime.now(UTC)

        parsed = isodatetime.to_datetime(result)
        assert before <= parsed <= after


class TestToDatestring:
    """Tests for to_datestring function."""

    def test_converts_date_to_iso_string(self):
        """Should convert date to YYYY-MM-DD format."""
        d = date(2025, 12, 23)
        result = isodatetime.to_datestring(d)
        assert result == "2025-12-23"

    def test_handles_various_dates(self):
        """Should handle different date values."""
        assert isodatetime.to_datestring(date(2025, 1, 1)) == "2025-01-01"
        assert isodatetime.to_datestring(date(2025, 12, 31)) == "2025-12-31"
        assert isodatetime.to_datestring(date(2020, 2, 29)) == "2020-02-29"  # Leap year

    def test_returns_string(self):
        """Should return a string."""
        result = isodatetime.to_datestring(date.today())
        assert isinstance(result, str)


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_datetime_to_timestamp_to_datetime(self):
        """Should preserve datetime through round-trip."""
        original = datetime(2025, 12, 23, 10, 30, 0, tzinfo=UTC)
        timestamp = isodatetime.to_timestamp(original)
        result = isodatetime.to_datetime(timestamp)
        assert result == original

    def test_naive_datetime_round_trip(self):
        """Naive datetime should become UTC-aware after round-trip."""
        original = datetime(2025, 12, 23, 10, 30, 0)
        timestamp = isodatetime.to_timestamp(original)
        result = isodatetime.to_datetime(timestamp)
        assert result.tzinfo == UTC
        # Time should be preserved
        assert result.hour == 10
        assert result.minute == 30

    def test_date_to_datestring_round_trip(self):
        """Date to datestring and back should preserve value."""
        original = date(2025, 12, 23)
        datestring = isodatetime.to_datestring(original)
        result = date.fromisoformat(datestring)
        assert result == original
