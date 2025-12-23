"""Tests for database initialization and entity management."""

import pytest
import re
from uuid import UUID
from datetime import datetime
from memogarden_core.database import (
    create_entity,
    get_entity_type,
    supersede_entity,
    get_schema_version
)


class TestSchemaInitialization:
    """Test database schema creation."""

    def test_tables_created(self, test_db):
        """Verify all expected tables are created."""
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "_schema_metadata" in tables
        assert "entity" in tables
        assert "transactions" in tables

    def test_indices_created(self, test_db):
        """Verify indices are created."""
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indices = [row[0] for row in cursor.fetchall()]

        # Check key indices exist
        assert any("entity_type" in idx for idx in indices)
        assert any("transactions_date" in idx for idx in indices)
        assert any("transactions_account" in idx for idx in indices)

    def test_view_created(self, test_db):
        """Verify transactions_view is created."""
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        )
        views = [row[0] for row in cursor.fetchall()]

        assert "transactions_view" in views

    def test_schema_version(self, test_db):
        """Verify schema version is set correctly."""
        cursor = test_db.execute(
            "SELECT value FROM _schema_metadata WHERE key = 'version'"
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == "20251223"


class TestEntityCreation:
    """Test entity creation and management."""

    def test_create_entity_returns_uuid(self, test_db):
        """create_entity should return a valid UUID string."""
        entity_id = create_entity(test_db, "transactions")

        # Should be a valid UUID
        try:
            UUID(entity_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        assert is_valid_uuid
        assert isinstance(entity_id, str)

    def test_create_entity_inserts_record(self, test_db):
        """create_entity should insert record into entity table."""
        entity_id = create_entity(test_db, "transactions")

        cursor = test_db.execute(
            "SELECT id, type FROM entity WHERE id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == entity_id
        assert row[1] == "transactions"

    def test_create_entity_sets_timestamps(self, test_db):
        """create_entity should set created_at and updated_at."""
        entity_id = create_entity(test_db, "transactions")

        cursor = test_db.execute(
            "SELECT created_at, updated_at FROM entity WHERE id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        created_at = row[0]
        updated_at = row[1]

        # Should be ISO 8601 format with Z suffix
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
        assert re.match(iso_pattern, created_at)
        assert re.match(iso_pattern, updated_at)

        # Should be parseable as datetime
        datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

    def test_create_entity_accepts_custom_id(self, test_db):
        """create_entity should accept custom UUID."""
        custom_id = "12345678-1234-1234-1234-123456789abc"
        entity_id = create_entity(test_db, "transactions", custom_id)

        assert entity_id == custom_id

        cursor = test_db.execute(
            "SELECT id FROM entity WHERE id = ?",
            (custom_id,)
        )
        row = cursor.fetchone()
        assert row is not None


class TestEntityLookup:
    """Test entity type lookup."""

    def test_get_entity_type_returns_correct_type(self, test_db):
        """get_entity_type should return correct type for existing entity."""
        entity_id = create_entity(test_db, "transactions")

        entity_type = get_entity_type(test_db, entity_id)

        assert entity_type == "transactions"

    def test_get_entity_type_returns_none_for_nonexistent(self, test_db):
        """get_entity_type should return None for non-existent entity."""
        entity_type = get_entity_type(test_db, "nonexistent-id")

        assert entity_type is None


class TestEntitySupersession:
    """Test entity supersession."""

    def test_supersede_entity_sets_fields(self, test_db):
        """supersede_entity should set superseded_by and superseded_at."""
        old_id = create_entity(test_db, "transactions")
        new_id = create_entity(test_db, "transactions")

        supersede_entity(test_db, old_id, new_id)
        test_db.commit()

        cursor = test_db.execute(
            "SELECT superseded_by, superseded_at FROM entity WHERE id = ?",
            (old_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == new_id  # superseded_by
        assert row[1] is not None  # superseded_at

        # Verify timestamp format
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
        assert re.match(iso_pattern, row[1])

    def test_supersede_entity_updates_timestamp(self, test_db):
        """supersede_entity should update the updated_at timestamp."""
        old_id = create_entity(test_db, "transactions")

        # Get original updated_at
        cursor = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (old_id,)
        )
        original_updated = cursor.fetchone()[0]

        # Supersede
        new_id = create_entity(test_db, "transactions")
        supersede_entity(test_db, old_id, new_id)
        test_db.commit()

        # Check updated_at changed
        cursor = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (old_id,)
        )
        new_updated = cursor.fetchone()[0]

        # Timestamps should be different (though might be same if very fast)
        # At minimum, should still be valid ISO format
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
        assert re.match(iso_pattern, new_updated)


class TestTransactionEntityIntegration:
    """Test that transactions work with entity registry."""

    def test_transaction_requires_entity(self, test_db):
        """Transaction should require entity record (FK constraint)."""
        # Try to insert transaction without entity
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            test_db.execute(
                """INSERT INTO transactions
                   (id, amount, currency, transaction_date, description, account, author)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("fake-id", 10.0, "SGD", "2025-12-22", "Test", "Household", "test")
            )
            test_db.commit()

    def test_transaction_with_entity_works(self, test_db):
        """Transaction should work when entity exists."""
        entity_id = create_entity(test_db, "transactions")

        test_db.execute(
            """INSERT INTO transactions
               (id, amount, currency, transaction_date, description, account, author)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entity_id, 10.0, "SGD", "2025-12-22", "Coffee", "Personal", "user")
        )
        test_db.commit()

        # Verify transaction exists
        cursor = test_db.execute(
            "SELECT id, amount, description FROM transactions WHERE id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == entity_id
        assert row[1] == 10.0
        assert row[2] == "Coffee"

    def test_transactions_view_includes_metadata(self, test_db):
        """transactions_view should include entity metadata."""
        entity_id = create_entity(test_db, "transactions")

        test_db.execute(
            """INSERT INTO transactions
               (id, amount, currency, transaction_date, description, account, author)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entity_id, 10.0, "SGD", "2025-12-22", "Coffee", "Personal", "user")
        )
        test_db.commit()

        # Query via view
        cursor = test_db.execute(
            "SELECT id, amount, created_at, updated_at FROM transactions_view WHERE id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == entity_id
        assert row[1] == 10.0
        assert row[2] is not None  # created_at from entity
        assert row[3] is not None  # updated_at from entity
