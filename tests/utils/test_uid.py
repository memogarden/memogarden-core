"""Tests for uid module."""

import re
import pytest
from memogarden_core.utils import uid


# UUID v4 pattern: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class TestGenerateUuid:
    """Tests for generate_uuid function."""

    def test_returns_string(self):
        """Should return a string."""
        result = uid.generate_uuid()
        assert isinstance(result, str)

    def test_returns_valid_uuid_v4_format(self):
        """Should match UUID v4 pattern."""
        result = uid.generate_uuid()
        assert UUID_PATTERN.match(result) is not None

    def test_returns_unique_values(self):
        """Multiple calls should return different values."""
        results = [uid.generate_uuid() for _ in range(100)]
        assert len(set(results)) == 100  # All unique

    def test_format_matches_expected_structure(self):
        """Should have hyphens in correct positions."""
        result = uid.generate_uuid()
        parts = result.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8   # 8 hex digits
        assert len(parts[1]) == 4   # 4 hex digits
        assert len(parts[2]) == 4   # 4 hex digits
        assert parts[2][0] == '4'   # UUID version 4
        assert len(parts[3]) == 4   # 4 hex digits
        assert len(parts[4]) == 12  # 12 hex digits
        assert parts[3][0] in '89ab'  # UUID variant
