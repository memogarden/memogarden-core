"""Tests for domain types in schema/types.py."""

import pytest
from datetime import datetime, date, UTC
from memogarden_core.schema.types import Timestamp, Date


class TestTimestamp:
    """Tests for Timestamp domain type."""

    def test_from_datetime_with_naive_datetime(self):
        """Test Timestamp.from_datetime() with naive datetime (treats as UTC)."""
        dt = datetime(2025, 12, 23, 10, 30, 45)
        ts = Timestamp.from_datetime(dt)
        assert ts == "2025-12-23T10:30:45Z"

    def test_from_datetime_with_aware_datetime(self):
        """Test Timestamp.from_datetime() with aware datetime."""
        dt = datetime(2025, 12, 23, 10, 30, 45, tzinfo=UTC)
        ts = Timestamp.from_datetime(dt)
        assert ts == "2025-12-23T10:30:45Z"

    def test_now_returns_valid_timestamp(self):
        """Test Timestamp.now() returns valid ISO 8601 timestamp."""
        ts = Timestamp.now()
        assert isinstance(ts, str)
        assert ts.endswith("Z")
        # Verify it's parseable
        dt = isodatetime.to_datetime(ts)
        assert isinstance(dt, datetime)

    def test_to_datetime(self):
        """Test Timestamp.to_datetime() round-trip conversion."""
        original_dt = datetime(2025, 12, 23, 10, 30, 45, tzinfo=UTC)
        ts = Timestamp.from_datetime(original_dt)
        result_dt = ts.to_datetime()
        assert result_dt == original_dt

    def test_timestamp_is_str_subtype(self):
        """Test that Timestamp is a string subtype."""
        ts = Timestamp.now()
        assert isinstance(ts, str)
        # Can use string operations
        assert ts.upper().endswith("Z")

    def test_from_datetime_with_microseconds(self):
        """Test Timestamp.from_datetime() preserves microseconds."""
        dt = datetime(2025, 12, 23, 10, 30, 45, 123456, tzinfo=UTC)
        ts = Timestamp.from_datetime(dt)
        # Microseconds should be included
        assert "123456" in ts

    def test_to_datetime_with_z_suffix(self):
        """Test Timestamp.to_datetime() handles Z suffix."""
        ts = Timestamp("2025-12-23T10:30:45Z")
        dt = ts.to_datetime()
        assert dt.year == 2025
        assert dt.month == 12
        assert dt.day == 23
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.second == 45


class TestDate:
    """Tests for Date domain type."""

    def test_from_date(self):
        """Test Date.from_date() converts date correctly."""
        d = date(2025, 12, 23)
        date_str = Date.from_date(d)
        assert date_str == "2025-12-23"

    def test_from_date_with_various_dates(self):
        """Test Date.from_date() with various dates."""
        test_cases = [
            (date(2025, 1, 1), "2025-01-01"),
            (date(2025, 12, 31), "2025-12-31"),
            (date(2020, 2, 29), "2020-02-29"),  # Leap year
        ]
        for d, expected in test_cases:
            assert Date.from_date(d) == expected

    def test_today(self):
        """Test Date.today() returns today's date."""
        today_date = Date.today()
        expected = date.today().isoformat()
        assert today_date == expected
        # Verify it's a valid Date string
        assert isinstance(today_date, str)
        assert len(today_date) == 10  # YYYY-MM-DD format

    def test_today_round_trip(self):
        """Test Date.today() round-trip conversion."""
        today_str = Date.today()
        today_date = today_str.to_date()
        assert today_date == date.today()

    def test_to_date(self):
        """Test Date.to_date() round-trip conversion."""
        original_date = date(2025, 12, 23)
        date_str = Date.from_date(original_date)
        result_date = date_str.to_date()
        assert result_date == original_date

    def test_date_is_str_subtype(self):
        """Test that Date is a string subtype."""
        d = Date.from_date(date(2025, 12, 23))
        assert isinstance(d, str)
        # Can use string operations
        assert d.startswith("2025")

    def test_to_date_from_string(self):
        """Test Date.to_date() parses ISO 8601 date strings."""
        date_str = Date("2025-12-23")
        d = date_str.to_date()
        assert d == date(2025, 12, 23)


class TestTimestampIntegration:
    """Integration tests for Timestamp type."""

    def test_timestamp_now_and_to_datetime_round_trip(self):
        """Test that now() and to_datetime() work together."""
        ts = Timestamp.now()
        dt = ts.to_datetime()
        # Convert back to timestamp
        ts2 = Timestamp.from_datetime(dt)
        # Should be identical (or very close)
        assert ts == ts2

    def test_timestamp_with_json_serialization(self):
        """Test that Timestamp works like a string for JSON."""
        ts = Timestamp("2025-12-23T10:30:45Z")
        # Should be serializable as string
        assert str(ts) == "2025-12-23T10:30:45Z"
        assert ts == "2025-12-23T10:30:45Z"


class TestDateIntegration:
    """Integration tests for Date type."""

    def test_date_from_to_round_trip(self):
        """Test Date round-trip conversion."""
        original = date(2025, 12, 23)
        date_str = Date.from_date(original)
        result = date_str.to_date()
        assert result == original

    def test_date_with_json_serialization(self):
        """Test that Date works like a string for JSON."""
        d = Date("2025-12-23")
        assert str(d) == "2025-12-23"
        assert d == "2025-12-23"


# Import isodatetime at module level for use in tests
from memogarden_core.utils import isodatetime
