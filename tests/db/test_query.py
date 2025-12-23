"""Tests for db/query.py query builders."""

import pytest

from memogarden_core.db.query import build_where_clause, build_update_clause


class TestBuildWhereClause:
    """Tests for build_where_clause function."""

    def test_empty_dict_returns_default_clause(self):
        """Empty conditions dict should return '1=1'."""
        clause, params = build_where_clause({})
        assert clause == "1=1"
        assert params == []

    def test_single_condition(self):
        """Single condition should generate simple equality."""
        clause, params = build_where_clause({"name": "John"})
        assert clause == "name = ?"
        assert params == ["John"]

    def test_multiple_conditions_joined_with_and(self):
        """Multiple conditions should be joined with AND."""
        clause, params = build_where_clause({"name": "John", "age": 30})
        assert clause == "name = ? AND age = ?"
        assert params == ["John", 30]

    def test_none_values_excluded(self):
        """None values should be excluded from the clause."""
        clause, params = build_where_clause({"name": "John", "age": None})
        assert clause == "name = ?"
        assert params == ["John"]

    def test_all_none_values_returns_default(self):
        """All None values should return default clause."""
        clause, params = build_where_clause({"name": None, "age": None})
        assert clause == "1=1"
        assert params == []

    def test_with_param_map(self):
        """param_map should provide custom SQL fragments."""
        clause, params = build_where_clause(
            {"name": "John"},
            param_map={"name": "t.name LIKE ?"}
        )
        assert clause == "t.name LIKE ?"
        assert params == ["John"]

    def test_mixed_param_map_and_default(self):
        """Mix of param_map and default behavior."""
        clause, params = build_where_clause(
            {"name": "John", "age": 30},
            param_map={"name": "t.name LIKE ?"}
        )
        assert clause == "t.name LIKE ? AND age = ?"
        assert params == ["John", 30]

    def test_param_map_key_not_in_conditions_ignored(self):
        """param_map keys not in conditions should be ignored."""
        clause, params = build_where_clause(
            {"age": 30},
            param_map={"name": "t.name LIKE ?"}
        )
        assert clause == "age = ?"
        assert params == [30]

    def test_none_value_with_param_map_excluded(self):
        """None values should be excluded even with param_map."""
        clause, params = build_where_clause(
            {"name": None},
            param_map={"name": "t.name LIKE ?"}
        )
        assert clause == "1=1"
        assert params == []

    def test_values_preserve_type(self):
        """Parameter values should preserve their types."""
        clause, params = build_where_clause({
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True
        })
        assert params == ["text", 42, 3.14, True]

    def test_special_characters_in_values(self):
        """Special characters should be preserved (parameterized)."""
        clause, params = build_where_clause({"name": "O'Brien"})
        assert clause == "name = ?"
        assert params == ["O'Brien"]

    def test_order_preserved(self):
        """Conditions should maintain dictionary order."""
        clause, params = build_where_clause({
            "a": 1,
            "b": 2,
            "c": 3
        })
        assert clause == "a = ? AND b = ? AND c = ?"
        assert params == [1, 2, 3]


class TestBuildUpdateClause:
    """Tests for build_update_clause function."""

    def test_empty_dict_returns_empty_clause(self):
        """Empty data dict should return empty clause."""
        clause, params = build_update_clause({})
        assert clause == ""
        assert params == []

    def test_single_field(self):
        """Single field should generate simple assignment."""
        clause, params = build_update_clause({"name": "John"})
        assert clause == "name = ?"
        assert params == ["John"]

    def test_multiple_fields_joined_with_comma(self):
        """Multiple fields should be joined with comma."""
        clause, params = build_update_clause({"name": "John", "age": 30})
        assert clause == "name = ?, age = ?"
        assert params == ["John", 30]

    def test_none_values_excluded(self):
        """None values should be excluded from the clause."""
        clause, params = build_update_clause({"name": "John", "age": None})
        assert clause == "name = ?"
        assert params == ["John"]

    def test_all_none_values_returns_empty(self):
        """All None values should return empty clause."""
        clause, params = build_update_clause({"name": None, "age": None})
        assert clause == ""
        assert params == []

    def test_exclude_single_field(self):
        """Excluded field should not be in clause."""
        clause, params = build_update_clause(
            {"name": "John", "id": 1},
            exclude={"id"}
        )
        assert clause == "name = ?"
        assert params == ["John"]

    def test_exclude_multiple_fields(self):
        """Multiple excluded fields should not be in clause."""
        clause, params = build_update_clause(
            {"name": "John", "age": 30, "id": 1},
            exclude={"id", "age"}
        )
        assert clause == "name = ?"
        assert params == ["John"]

    def test_exclude_field_with_none_value(self):
        """Field excluded even if value is None."""
        clause, params = build_update_clause(
            {"name": "John", "id": None},
            exclude={"id"}
        )
        assert clause == "name = ?"
        assert params == ["John"]

    def test_empty_exclude_set(self):
        """Empty exclude set should not filter anything."""
        clause, params = build_update_clause(
            {"name": "John", "age": 30},
            exclude=set()
        )
        assert clause == "name = ?, age = ?"
        assert params == ["John", 30]

    def test_none_exclude_treated_as_empty_set(self):
        """None exclude should be treated as empty set."""
        clause, params = build_update_clause(
            {"name": "John", "age": 30},
            exclude=None
        )
        assert clause == "name = ?, age = ?"
        assert params == ["John", 30]

    def test_values_preserve_type(self):
        """Parameter values should preserve their types."""
        clause, params = build_update_clause({
            "string": "text",
            "int": 42,
            "float": 3.14,
            "bool": True
        })
        assert params == ["text", 42, 3.14, True]

    def test_special_characters_in_values(self):
        """Special characters should be preserved (parameterized)."""
        clause, params = build_update_clause({"name": "O'Brien"})
        assert clause == "name = ?"
        assert params == ["O'Brien"]

    def test_order_preserved(self):
        """Fields should maintain dictionary order."""
        clause, params = build_update_clause({
            "a": 1,
            "b": 2,
            "c": 3
        })
        assert clause == "a = ?, b = ?, c = ?"
        assert params == [1, 2, 3]


class TestSQLInjectionSafety:
    """Tests to verify SQL injection safety through parameterization."""

    def test_where_clause_parameterizes_values(self):
        """Values should be parameterized, not interpolated."""
        clause, params = build_where_clause({"name": "'; DROP TABLE users; --"})
        # The malicious SQL should be in params, not in the clause
        assert clause == "name = ?"
        assert params == ["'; DROP TABLE users; --"]
        assert "DROP TABLE" not in clause

    def test_update_clause_parameterizes_values(self):
        """Values should be parameterized, not interpolated."""
        clause, params = build_update_clause({"name": "'; DROP TABLE users; --"})
        # The malicious SQL should be in params, not in the clause
        assert clause == "name = ?"
        assert params == ["'; DROP TABLE users; --"]
        assert "DROP TABLE" not in clause

    def test_param_map_values_parameterized(self):
        """Even with param_map, values should be parameterized."""
        clause, params = build_where_clause(
            {"name": "'; DROP TABLE users; --"},
            param_map={"name": "t.name LIKE ?"}
        )
        assert clause == "t.name LIKE ?"
        assert params == ["'; DROP TABLE users; --"]
        assert "DROP TABLE" not in clause

    def test_field_names_not_escaped(self):
        """Field names are not parameterized (this is expected).
        Caller is responsible for validating field names come from trusted source.
        """
        # This test documents current behavior - field names are interpolated
        clause, params = build_where_clause({"name": "value"})
        assert "name" in clause  # Field name is in the clause
        assert params == ["value"]  # Only value is parameterized
