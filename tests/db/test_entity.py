"""Tests for db/entity.py EntityOperations class."""

import pytest

from memogarden_core.db.entity import EntityOperations
from memogarden_core.exceptions import ResourceNotFound


class TestEntityCreate:
    """Tests for EntityOperations.create() method."""

    def test_create_generates_uuid(self, test_db):
        """create() should generate a valid UUID v4."""
        ops = EntityOperations(test_db)
        entity_id = ops.create("transactions")

        assert entity_id is not None
        # Verify it's a valid UUID v4 format
        assert len(entity_id) == 36
        assert entity_id.count("-") == 4

    def test_create_inserts_correct_values(self, test_db):
        """create() should insert correct values in entity table."""
        ops = EntityOperations(test_db)

        # Create parent and group entities first for FK constraints
        group_id = ops.create("groups")
        derived_from = ops.create("transactions")

        entity_id = ops.create(
            "transactions",
            group_id=group_id,
            derived_from=derived_from
        )

        row = test_db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()

        assert row["id"] == entity_id
        assert row["type"] == "transactions"
        assert row["group_id"] == group_id
        assert row["derived_from"] == derived_from
        assert row["superseded_by"] is None
        assert row["superseded_at"] is None
        assert row["created_at"] is not None
        assert row["updated_at"] is not None

    def test_create_with_optional_params_none(self, test_db):
        """create() should handle None values for optional params."""
        ops = EntityOperations(test_db)
        entity_id = ops.create(
            "transactions",
            group_id=None,
            derived_from=None
        )

        row = test_db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()

        assert row["group_id"] is None
        assert row["derived_from"] is None

    def test_create_handles_uuid_collision_rarely(self, test_db):
        """create() should retry on UUID collision (extremely rare)."""
        import sqlite3

        ops = EntityOperations(test_db)

        # Generate a UUID first
        entity_id = ops.create("transactions")

        # Manually insert a duplicate to simulate collision scenario
        # This tests the retry logic (though in practice collisions are astronomically rare)
        # We can't truly test this without mocking uid.generate_uuid(), but the
        # retry logic is there for safety

        # The best we can do is verify that repeated creates all work
        ids = []
        for i in range(10):
            new_id = ops.create("transactions")
            ids.append(new_id)

        # All IDs should be unique
        assert len(set(ids)) == 10


class TestEntityGetById:
    """Tests for EntityOperations.get_by_id() method."""

    def test_get_by_id_returns_row_for_existing_entity(self, test_db):
        """get_by_id() should return row for existing entity."""
        ops = EntityOperations(test_db)
        entity_id = ops.create("transactions")

        row = ops.get_by_id(entity_id)

        assert row is not None
        assert row["id"] == entity_id
        assert row["type"] == "transactions"

    def test_get_by_id_raises_resource_not_found_for_non_existent(self, test_db):
        """get_by_id() should raise ResourceNotFound for non-existent entity."""
        ops = EntityOperations(test_db)

        with pytest.raises(ResourceNotFound) as exc_info:
            ops.get_by_id("non-existent-id")

        assert "non-existent-id" in str(exc_info.value.message)
        assert exc_info.value.details == {"entity_id": "non-existent-id"}

    def test_get_by_id_with_custom_table_or_view(self, test_db):
        """get_by_id() should query custom table/view when specified."""
        ops = EntityOperations(test_db)
        entity_id = ops.create("transactions")

        # Add a transaction record
        test_db.execute(
            """INSERT INTO transactions (id, amount, currency, transaction_date, description, account, author)
               VALUES (?, 100.0, 'SGD', '2025-12-23', 'Test', 'Household', 'system')""",
            (entity_id,)
        )

        # Query via transactions_view
        row = ops.get_by_id(entity_id, table_or_view="transactions_view", entity_type="Transaction")

        assert row is not None
        assert row["id"] == entity_id
        assert "amount" in row.keys()

    def test_get_by_id_with_custom_entity_type(self, test_db):
        """get_by_id() should use custom entity_type in error message."""
        ops = EntityOperations(test_db)

        with pytest.raises(ResourceNotFound) as exc_info:
            ops.get_by_id("non-existent", entity_type="CustomEntity")

        assert "CustomEntity" in str(exc_info.value.message)


class TestEntitySupersede:
    """Tests for EntityOperations.supersede() method."""

    def test_supersede_updates_superseded_by_and_superseded_at(self, test_db):
        """supersede() should update superseded_by and superseded_at."""
        ops = EntityOperations(test_db)
        old_id = ops.create("transactions")
        new_id = ops.create("transactions")

        ops.supersede(old_id, new_id)

        row = test_db.execute("SELECT * FROM entity WHERE id = ?", (old_id,)).fetchone()
        assert row["superseded_by"] == new_id
        assert row["superseded_at"] is not None

    def test_supersede_updates_updated_at(self, test_db):
        """supersede() should update the updated_at timestamp."""
        ops = EntityOperations(test_db)
        old_id = ops.create("transactions")
        new_id = ops.create("transactions")

        # Get original updated_at
        original_row = test_db.execute("SELECT updated_at FROM entity WHERE id = ?", (old_id,)).fetchone()
        original_updated_at = original_row["updated_at"]

        # Supersede
        ops.supersede(old_id, new_id)

        # Check updated_at changed
        updated_row = test_db.execute("SELECT updated_at FROM entity WHERE id = ?", (old_id,)).fetchone()
        assert updated_row["updated_at"] != original_updated_at


class TestEntityUpdateTimestamp:
    """Tests for EntityOperations.update_timestamp() method."""

    def test_update_timestamp_updates_updated_at(self, test_db):
        """update_timestamp() should update the updated_at field."""
        ops = EntityOperations(test_db)
        entity_id = ops.create("transactions")

        # Get original updated_at
        original_row = test_db.execute("SELECT updated_at FROM entity WHERE id = ?", (entity_id,)).fetchone()
        original_updated_at = original_row["updated_at"]

        # Update timestamp
        ops.update_timestamp(entity_id)

        # Check updated_at changed
        updated_row = test_db.execute("SELECT updated_at FROM entity WHERE id = ?", (entity_id,)).fetchone()
        assert updated_row["updated_at"] != original_updated_at

    def test_update_timestamp_does_not_change_other_fields(self, test_db):
        """update_timestamp() should only change updated_at field."""
        ops = EntityOperations(test_db)

        # Create parent entities for FK constraints
        group_id = ops.create("groups")
        derived_from = ops.create("transactions")

        entity_id = ops.create(
            "transactions",
            group_id=group_id,
            derived_from=derived_from
        )

        # Get original values
        original_row = test_db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()

        # Update timestamp
        ops.update_timestamp(entity_id)

        # Check other fields unchanged
        updated_row = test_db.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
        assert updated_row["id"] == original_row["id"]
        assert updated_row["type"] == original_row["type"]
        assert updated_row["group_id"] == original_row["group_id"]
        assert updated_row["derived_from"] == original_row["derived_from"]
        assert updated_row["created_at"] == original_row["created_at"]


class TestEntityIntegration:
    """Integration tests for EntityOperations."""

    def test_full_entity_lifecycle(self, test_db):
        """Test complete lifecycle: create, get, supersede, update."""
        ops = EntityOperations(test_db)

        # Create
        entity_id = ops.create("transactions")
        assert entity_id is not None

        # Get
        row = ops.get_by_id(entity_id)
        assert row["type"] == "transactions"

        # Create another and supersede
        new_id = ops.create("transactions")
        ops.supersede(entity_id, new_id)

        # Verify superseded
        row = ops.get_by_id(entity_id)
        assert row["superseded_by"] == new_id

        # Update timestamp on new entity
        ops.update_timestamp(new_id)
        row = ops.get_by_id(new_id)
        assert row["updated_at"] is not None

    def test_multiple_entities_same_type(self, test_db):
        """Test creating multiple entities of the same type."""
        ops = EntityOperations(test_db)

        ids = []
        for i in range(5):
            entity_id = ops.create("transactions")
            ids.append(entity_id)

        # Verify all exist
        for entity_id in ids:
            row = ops.get_by_id(entity_id)
            assert row["type"] == "transactions"

        # Verify count
        count = test_db.execute(
            "SELECT COUNT(*) FROM entity WHERE type = ?",
            ("transactions",)
        ).fetchone()[0]
        assert count == 5

    def test_different_entity_types(self, test_db):
        """Test creating entities with different types."""
        ops = EntityOperations(test_db)

        transaction_id = ops.create("transactions")
        recurrence_id = ops.create("recurrences")

        # Verify types
        transaction_row = ops.get_by_id(transaction_id)
        assert transaction_row["type"] == "transactions"

        recurrence_row = ops.get_by_id(recurrence_id)
        assert recurrence_row["type"] == "recurrences"
