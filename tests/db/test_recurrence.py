"""Tests for db/recurrence.py RecurrenceOperations class.

These tests follow the behavior-focused testing philosophy:
- No mocks, use real database operations
- Test observable behavior (inputs → outputs)
- Use in-memory SQLite for isolation
"""

import json
import pytest
from datetime import datetime

from memogarden.db.recurrence import RecurrenceOperations
from memogarden.db.entity import EntityOperations
from memogarden.db import Core
from memogarden.exceptions import ResourceNotFound


class TestRecurrenceGetById:
    """Tests for RecurrenceOperations.get_by_id() method."""

    def test_get_by_id_returns_recurrence_for_existing_id(self, test_db):
        """get_by_id() should return recurrence for existing ID."""
        entity_ops = EntityOperations(test_db)
        rec_ops = RecurrenceOperations(test_db, core=None)

        # Create entity first
        entity_id = entity_ops.create("recurrences")

        # Manually insert recurrence (since we don't have Core reference)
        rrule = "FREQ=MONTHLY;BYDAY=2FR"
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        test_db.execute(
            """INSERT INTO recurrences
               (id, rrule, entities, valid_from, valid_until)
               VALUES (?, ?, ?, ?, NULL)""",
            (entity_id, rrule, entities, "2025-01-01T00:00:00Z")
        )

        # Get by ID
        row = rec_ops.get_by_id(entity_id)

        assert row is not None
        assert row["id"] == entity_id
        assert row["rrule"] == rrule
        assert row["entities"] == entities

    def test_get_by_id_raises_resource_not_found_for_non_existent(self, test_db):
        """get_by_id() should raise ResourceNotFound for non-existent ID."""
        rec_ops = RecurrenceOperations(test_db, core=None)

        with pytest.raises(ResourceNotFound) as exc_info:
            rec_ops.get_by_id("non-existent-id")

        assert "non-existent-id" in str(exc_info.value.message)
        assert exc_info.value.details == {"recurrence_id": "non-existent-id"}


class TestRecurrenceCreate:
    """Tests for RecurrenceOperations.create() method."""

    def test_create_returns_uuid(self, test_db):
        """create() should return UUID when using Core."""
        core = Core(test_db)
        rrule = "FREQ=MONTHLY;BYDAY=2FR"
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(
            rrule=rrule,
            entities=entities,
            valid_from=valid_from,
        )

        assert isinstance(recurrence_id, str)
        assert len(recurrence_id) == 36  # UUID v4 format

    def test_create_creates_entity_entry(self, test_db):
        """create() should create entity registry entry."""
        core = Core(test_db)
        rrule = "FREQ=MONTHLY;BYDAY=2FR"
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(
            rrule=rrule,
            entities=entities,
            valid_from=valid_from,
        )

        row = test_db.execute(
            "SELECT * FROM entity WHERE id = ?",
            (recurrence_id,)
        ).fetchone()

        assert row is not None
        assert row["type"] == "recurrences"

    def test_create_inserts_record(self, test_db):
        """create() should insert recurrence record."""
        core = Core(test_db)
        rrule = "FREQ=MONTHLY;BYDAY=2FR"
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(
            rrule=rrule,
            entities=entities,
            valid_from=valid_from,
        )

        row = test_db.execute(
            "SELECT * FROM recurrences WHERE id = ?",
            (recurrence_id,)
        ).fetchone()

        assert row is not None
        assert row["rrule"] == rrule
        assert row["entities"] == entities
        assert row["valid_from"] == "2025-01-01T00:00:00Z"

    def test_create_with_valid_until(self, test_db):
        """create() should handle valid_until field."""
        core = Core(test_db)
        rrule = "FREQ=MONTHLY;BYDAY=2FR"
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)
        valid_until = datetime(2025, 12, 31, 23, 59, 59)

        recurrence_id = core.recurrence.create(
            rrule=rrule,
            entities=entities,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        row = test_db.execute(
            "SELECT * FROM recurrences WHERE id = ?",
            (recurrence_id,)
        ).fetchone()

        assert row["valid_until"] == "2025-12-31T23:59:59Z"


class TestRecurrenceList:
    """Tests for RecurrenceOperations.list() method."""

    def test_list_returns_all_recurrences(self, test_db):
        """list() should return all recurrences."""
        entity_ops = EntityOperations(test_db)
        rec_ops = RecurrenceOperations(test_db, core=None)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])

        # Create multiple recurrences
        for rrule in ["FREQ=MONTHLY;BYDAY=2FR", "FREQ=WEEKLY;BYDAY=MO", "FREQ=DAILY"]:
            entity_id = entity_ops.create("recurrences")
            test_db.execute(
                "INSERT INTO recurrences (id, rrule, entities, valid_from) VALUES (?, ?, ?, ?)",
                (entity_id, rrule, entities, "2025-01-01T00:00:00Z")
            )

        rows = rec_ops.list(filters={}, limit=100, offset=0)

        assert len(rows) == 3

    def test_list_filters_by_valid_from(self, test_db):
        """list() should filter by valid_from."""
        entity_ops = EntityOperations(test_db)
        rec_ops = RecurrenceOperations(test_db, core=None)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])

        # Create recurrences with different valid_from dates
        for i, valid_from in enumerate(["2025-01-01T00:00:00Z", "2025-02-01T00:00:00Z", "2025-03-01T00:00:00Z"]):
            entity_id = entity_ops.create("recurrences")
            test_db.execute(
                "INSERT INTO recurrences (id, rrule, entities, valid_from) VALUES (?, ?, ?, ?)",
                (entity_id, f"FREQ=DAILY;INTERVAL={i+1}", entities, valid_from)
            )

        rows = rec_ops.list(filters={"valid_from": "2025-02-01T00:00:00Z"}, limit=100, offset=0)

        assert len(rows) == 2  # Feb and March

    def test_list_excludes_superseded_by_default(self, test_db):
        """list() should exclude superseded recurrences by default."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        # Create recurrence and supersede it
        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)
        tombstone_id = core.entity.create("recurrences")
        core.entity.supersede(recurrence_id, tombstone_id)

        # Create another non-superseded recurrence
        core.recurrence.create(rrule="FREQ=WEEKLY", entities=entities, valid_from=valid_from)

        rec_ops = RecurrenceOperations(test_db, core=None)
        rows = rec_ops.list(filters={}, limit=100, offset=0)

        assert len(rows) == 1  # Only the non-superseded one

    def test_list_includes_superseded_when_flag_set(self, test_db):
        """list() should include superseded recurrences when flag is set."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        # Create recurrence and supersede it
        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)
        tombstone_id = core.entity.create("recurrences")
        core.entity.supersede(recurrence_id, tombstone_id)

        rec_ops = RecurrenceOperations(test_db, core=None)
        rows = rec_ops.list(filters={"include_superseded": True}, limit=100, offset=0)

        assert len(rows) == 1  # Superseded one is included

    def test_list_with_limit_and_offset(self, test_db):
        """list() should respect limit and offset."""
        entity_ops = EntityOperations(test_db)
        rec_ops = RecurrenceOperations(test_db, core=None)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])

        # Create 5 recurrences
        for i in range(5):
            entity_id = entity_ops.create("recurrences")
            test_db.execute(
                "INSERT INTO recurrences (id, rrule, entities, valid_from) VALUES (?, ?, ?, ?)",
                (entity_id, f"FREQ=DAILY;INTERVAL={i+1}", entities, "2025-01-01T00:00:00Z")
            )

        rows = rec_ops.list(filters={}, limit=2, offset=1)

        assert len(rows) == 2


class TestRecurrenceUpdate:
    """Tests for RecurrenceOperations.update() method."""

    def test_update_updates_only_provided_fields(self, test_db):
        """update() should only update provided fields."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)

        # Update only rrule
        core.recurrence.update(recurrence_id, {"rrule": "FREQ=WEEKLY"})

        row = core.recurrence.get_by_id(recurrence_id)
        assert row["rrule"] == "FREQ=WEEKLY"
        assert row["entities"] == entities  # Unchanged

    def test_update_skips_none_values(self, test_db):
        """update() should skip fields with None values (don't update)."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)
        valid_until = datetime(2025, 12, 31, 23, 59, 59)

        recurrence_id = core.recurrence.create(
            rrule="FREQ=MONTHLY",
            entities=entities,
            valid_from=valid_from,
            valid_until=valid_until,
        )

        # Try to set valid_until to None (should be skipped, not updated)
        core.recurrence.update(recurrence_id, {"valid_until": None})

        row = core.recurrence.get_by_id(recurrence_id)
        # valid_until should remain unchanged (None values are skipped)
        assert row["valid_until"] == "2025-12-31T23:59:59Z"

    def test_update_excludes_id_field(self, test_db):
        """update() should exclude id field from updates."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)

        # Try to update id (should be ignored)
        core.recurrence.update(recurrence_id, {"id": "different-id", "rrule": "FREQ=WEEKLY"})

        row = core.recurrence.get_by_id(recurrence_id)
        assert row["id"] == recurrence_id  # ID unchanged

    def test_update_converts_datetime_to_string(self, test_db):
        """update() should convert datetime fields to ISO strings."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)

        # Update with datetime object
        new_valid_until = datetime(2025, 12, 31, 23, 59, 59)
        core.recurrence.update(recurrence_id, {"valid_until": new_valid_until})

        row = core.recurrence.get_by_id(recurrence_id)
        assert row["valid_until"] == "2025-12-31T23:59:59Z"

    def test_update_updates_entity_updated_at(self, test_db):
        """update() should update entity.updated_at timestamp."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)

        # Get original updated_at
        row_before = core.recurrence.get_by_id(recurrence_id)
        updated_at_before = row_before["updated_at"]

        # Update
        core.recurrence.update(recurrence_id, {"rrule": "FREQ=WEEKLY"})

        # Get updated timestamp
        row_after = core.recurrence.get_by_id(recurrence_id)
        updated_at_after = row_after["updated_at"]

        assert updated_at_after != updated_at_before

    def test_update_with_empty_dict_does_nothing(self, test_db):
        """update() with empty dict shouldn't change anything."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)

        # Get original values
        row_before = core.recurrence.get_by_id(recurrence_id)
        rrule_before = row_before["rrule"]
        updated_at_before = row_before["updated_at"]

        # Update with empty dict
        core.recurrence.update(recurrence_id, {})

        # Get values after
        row_after = core.recurrence.get_by_id(recurrence_id)
        rrule_after = row_after["rrule"]
        updated_at_after = row_after["updated_at"]

        assert rrule_after == rrule_before
        # updated_at should NOT change when no fields are updated
        assert updated_at_after == updated_at_before


class TestRecurrenceIntegration:
    """Integration tests for full recurrence lifecycle."""

    def test_full_recurrence_lifecycle(self, test_db):
        """Test create, read, update, delete lifecycle."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        # Create
        recurrence_id = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)

        # Read
        row = core.recurrence.get_by_id(recurrence_id)
        assert row["rrule"] == "FREQ=MONTHLY"

        # Update
        core.recurrence.update(recurrence_id, {"rrule": "FREQ=WEEKLY"})
        row = core.recurrence.get_by_id(recurrence_id)
        assert row["rrule"] == "FREQ=WEEKLY"

        # Delete (supersede)
        tombstone_id = core.entity.create("recurrences")
        core.entity.supersede(recurrence_id, tombstone_id)

        # Verify superseded
        row = core.recurrence.get_by_id(recurrence_id)
        assert row["superseded_by"] == tombstone_id

    def test_list_with_superseded_recurrences(self, test_db):
        """Test that list correctly handles mix of active and superseded."""
        core = Core(test_db)
        entities = json.dumps([{"amount": -1500, "description": "Rent"}])
        valid_from = datetime(2025, 1, 1, 0, 0, 0)

        # Create 3 recurrences
        r1 = core.recurrence.create(rrule="FREQ=MONTHLY", entities=entities, valid_from=valid_from)
        r2 = core.recurrence.create(rrule="FREQ=WEEKLY", entities=entities, valid_from=valid_from)
        r3 = core.recurrence.create(rrule="FREQ=DAILY", entities=entities, valid_from=valid_from)

        # Supersede one
        tombstone = core.entity.create("recurrences")
        core.entity.supersede(r1, tombstone)

        # List all (excluding superseded)
        rows = core.recurrence.list(filters={}, limit=100, offset=0)
        assert len(rows) == 2

        # List all (including superseded)
        rows = core.recurrence.list(filters={"include_superseded": True}, limit=100, offset=0)
        assert len(rows) == 3
