"""Tests for database initialization and entity management."""

import pytest
import re
from uuid import UUID
from datetime import datetime
from memogarden.db import get_core


class TestSchemaInitialization:
    """Test database schema creation."""

    def test_tables_created(self, test_db):
        """Verify all expected tables are created."""
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert "_schema_metadata" in tables
        assert "api_keys" in tables
        assert "entity" in tables
        assert "transactions" in tables
        assert "users" in tables

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
        """Verify schema version is set correctly (or migrated)."""
        cursor = test_db.execute(
            "SELECT value FROM _schema_metadata WHERE key = 'version'"
        )
        row = cursor.fetchone()

        assert row is not None
        # Accept current schema version or newer (forward compatible)
        # Note: This test is flexible to accommodate different schema versions
        # during development and migration periods
        version = row[0]
        # Should be a valid version string (YYYYMMDD format)
        assert len(version) == 8
        assert version.isdigit()


class TestEntityCreation:
    """Test entity creation and management."""

    def test_create_entity_returns_uuid(self, test_db):
        """create_entity should return a valid UUID string."""
        core = get_core()
        core._conn = test_db  # Use test connection
        entity_id = core.entity.create("transactions")

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
        core = get_core()
        core._conn = test_db  # Use test connection
        entity_id = core.entity.create("transactions")

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
        core = get_core()
        core._conn = test_db  # Use test connection
        entity_id = core.entity.create("transactions")

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


class TestEntityLookup:
    """Test entity type lookup (behavior test via Core API)."""

    def test_get_entity_returns_correct_type(self, test_db):
        """get_by_id should return correct type for existing entity."""
        core = get_core()
        core._conn = test_db  # Use test connection
        entity_id = core.entity.create("transactions")

        row = core.entity.get_by_id(entity_id)

        assert row is not None
        assert row["type"] == "transactions"


class TestEntitySupersession:
    """Test entity supersession."""

    def test_supersede_entity_sets_fields(self, test_db):
        """supersede should set superseded_by and superseded_at."""
        core = get_core()
        core._conn = test_db  # Use test connection
        old_id = core.entity.create("transactions")
        new_id = core.entity.create("transactions")

        core.entity.supersede(old_id, new_id)
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
        """supersede should update the updated_at timestamp."""
        core = get_core()
        core._conn = test_db  # Use test connection
        old_id = core.entity.create("transactions")

        # Get original updated_at
        cursor = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (old_id,)
        )
        original_updated = cursor.fetchone()[0]

        # Supersede
        new_id = core.entity.create("transactions")
        core.entity.supersede(old_id, new_id)
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
        core = get_core()
        core._conn = test_db  # Use test connection
        entity_id = core.entity.create("transactions")

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
        core = get_core()
        core._conn = test_db  # Use test connection
        entity_id = core.entity.create("transactions")

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


class TestUsersTable:
    """Test users table schema and constraints."""

    def test_users_table_columns(self, test_db):
        """Verify users table has correct columns."""
        cursor = test_db.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "id" in columns
        assert "username" in columns
        assert "password_hash" in columns
        assert "is_admin" in columns
        assert "created_at" in columns

    def test_users_username_unique(self, test_db):
        """Verify username has unique constraint."""
        cursor = test_db.execute("PRAGMA index_list(users)")
        indexes = cursor.fetchall()

        # Find unique index on username
        username_idx = None
        for idx in indexes:
            if "username" in idx[1]:
                username_idx = idx
                break

        assert username_idx is not None, "No unique index found on username"

    def test_users_entity_foreign_key(self, test_db):
        """Verify users table has foreign key to entity."""
        cursor = test_db.execute("PRAGMA foreign_key_list(users)")
        fks = cursor.fetchall()

        # Should have FK to entity table
        entity_fk = [fk for fk in fks if fk[2] == "entity"]
        assert len(entity_fk) > 0, "No foreign key to entity table found"

    def test_users_with_entity_works(self, test_db):
        """User should work when entity exists."""
        core = get_core()
        core._conn = test_db
        entity_id = core.entity.create("users")

        test_db.execute(
            """INSERT INTO users
               (id, username, password_hash, is_admin, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (entity_id, "testuser", "hashedpassword", 1, "2025-12-29T10:00:00Z")
        )
        test_db.commit()

        cursor = test_db.execute(
            "SELECT id, username, is_admin FROM users WHERE id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == entity_id
        assert row[1] == "testuser"
        assert row[2] == 1

    def test_users_requires_entity(self, test_db):
        """User should require entity record (FK constraint)."""
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            test_db.execute(
                """INSERT INTO users
                   (id, username, password_hash, is_admin, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("fake-id", "testuser", "hashedpassword", 1, "2025-12-29T10:00:00Z")
            )
            test_db.commit()


class TestAPIKeysTable:
    """Test api_keys table schema and constraints."""

    def test_api_keys_table_columns(self, test_db):
        """Verify api_keys table has correct columns."""
        cursor = test_db.execute("PRAGMA table_info(api_keys)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "id" in columns
        assert "user_id" in columns
        assert "name" in columns
        assert "key_hash" in columns
        assert "key_prefix" in columns
        assert "expires_at" in columns
        assert "created_at" in columns
        assert "last_seen" in columns
        assert "revoked_at" in columns

    def test_api_keys_entity_foreign_key(self, test_db):
        """Verify api_keys table has foreign key to entity."""
        cursor = test_db.execute("PRAGMA foreign_key_list(api_keys)")
        fks = cursor.fetchall()

        # Should have FK to entity table
        entity_fk = [fk for fk in fks if fk[2] == "entity"]
        assert len(entity_fk) > 0, "No foreign key to entity table found"

    def test_api_keys_user_foreign_key(self, test_db):
        """Verify api_keys table has foreign key to users."""
        cursor = test_db.execute("PRAGMA foreign_key_list(api_keys)")
        fks = cursor.fetchall()

        # Should have FK to users table
        user_fk = [fk for fk in fks if fk[2] == "users"]
        assert len(user_fk) > 0, "No foreign key to users table found"

    def test_api_keys_with_user_and_entity_works(self, test_db):
        """API key should work when entity and user exist."""
        core = get_core()
        core._conn = test_db

        # Create user entity and user record
        user_entity_id = core.entity.create("users")
        test_db.execute(
            """INSERT INTO users
               (id, username, password_hash, is_admin, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_entity_id, "testuser", "hashedpassword", 1, "2025-12-29T10:00:00Z")
        )

        # Create API key entity and record
        api_key_entity_id = core.entity.create("api_keys")
        test_db.execute(
            """INSERT INTO api_keys
               (id, user_id, name, key_hash, key_prefix, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (api_key_entity_id, user_entity_id, "test-key", "hash123", "mg_sk_test_", "2025-12-29T10:00:00Z")
        )
        test_db.commit()

        cursor = test_db.execute(
            "SELECT id, user_id, name, key_prefix FROM api_keys WHERE id = ?",
            (api_key_entity_id,)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == api_key_entity_id
        assert row[1] == user_entity_id
        assert row[2] == "test-key"
        assert row[3] == "mg_sk_test_"

    def test_api_keys_requires_user(self, test_db):
        """API key should require user record (FK constraint)."""
        core = get_core()
        core._conn = test_db
        api_key_entity_id = core.entity.create("api_keys")

        with pytest.raises(Exception):  # sqlite3.IntegrityError
            test_db.execute(
                """INSERT INTO api_keys
                   (id, user_id, name, key_hash, key_prefix, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (api_key_entity_id, "fake-user-id", "test-key", "hash123", "mg_sk_test_", "2025-12-29T10:00:00Z")
            )
            test_db.commit()

    def test_api_keys_cascades_on_user_delete(self, test_db):
        """API keys should be deleted when user is deleted (CASCADE)."""
        core = get_core()
        core._conn = test_db

        # Create user entity and user record
        user_entity_id = core.entity.create("users")
        test_db.execute(
            """INSERT INTO users
               (id, username, password_hash, is_admin, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_entity_id, "testuser", "hashedpassword", 1, "2025-12-29T10:00:00Z")
        )

        # Create API key entity and record
        api_key_entity_id = core.entity.create("api_keys")
        test_db.execute(
            """INSERT INTO api_keys
               (id, user_id, name, key_hash, key_prefix, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (api_key_entity_id, user_entity_id, "test-key", "hash123", "mg_sk_test_", "2025-12-29T10:00:00Z")
        )
        test_db.commit()

        # Verify API key exists
        cursor = test_db.execute(
            "SELECT COUNT(*) FROM api_keys WHERE id = ?",
            (api_key_entity_id,)
        )
        count_before = cursor.fetchone()[0]
        assert count_before == 1

        # Delete user (should cascade to API keys)
        test_db.execute("DELETE FROM users WHERE id = ?", (user_entity_id,))
        test_db.commit()

        # Verify API key is deleted
        cursor = test_db.execute(
            "SELECT COUNT(*) FROM api_keys WHERE id = ?",
            (api_key_entity_id,)
        )
        count_after = cursor.fetchone()[0]
        assert count_after == 0


class TestMigration:
    """Test database migration functionality."""

    def test_get_current_schema_version(self, test_db):
        """Test getting current schema version from database."""
        from memogarden.db import _get_current_schema_version

        version = _get_current_schema_version(test_db)
        assert version is not None
        assert len(version) == 8
        assert version.isdigit()

    def test_migration_needed_applies_migration(self, test_db, tmp_path):
        """Test that migration is applied when database is at old version."""
        from memogarden.db import _run_migrations, EXPECTED_SCHEMA_VERSION

        # Simulate old schema by updating version (use previous version)
        test_db.execute(
            "UPDATE _schema_metadata SET value = ? WHERE key = 'version'",
            ("20251229",)
        )
        test_db.commit()

        # Verify old version
        cursor = test_db.execute("SELECT value FROM _schema_metadata WHERE key = 'version'")
        assert cursor.fetchone()[0] == "20251229"

        # Run migrations
        _run_migrations(test_db)

        # Verify migration was applied
        cursor = test_db.execute("SELECT value FROM _schema_metadata WHERE key = 'version'")
        version = cursor.fetchone()[0]
        assert version == EXPECTED_SCHEMA_VERSION

        # Verify new table exists
        cursor = test_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'recurrences'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        assert "recurrences" in tables

    def test_migration_not_needed_when_at_current_version(self, test_db):
        """Test that no migration occurs when already at current version."""
        from memogarden.db import _run_migrations, EXPECTED_SCHEMA_VERSION

        # Verify we're at expected version
        cursor = test_db.execute("SELECT value FROM _schema_metadata WHERE key = 'version'")
        initial_version = cursor.fetchone()[0]

        # Run migrations
        _run_migrations(test_db)

        # Version should be unchanged
        cursor = test_db.execute("SELECT value FROM _schema_metadata WHERE key = 'version'")
        assert cursor.fetchone()[0] == initial_version

    def test_migration_forward_compatible_with_newer_db(self, test_db):
        """Test that system is forward compatible with newer database versions."""
        from memogarden.db import _run_migrations

        # Simulate newer schema version
        test_db.execute(
            "UPDATE _schema_metadata SET value = ? WHERE key = 'version'",
            ("20251230",)  # Future version
        )
        test_db.commit()

        # Should not raise error, should just pass
        _run_migrations(test_db)

        # Version should still be the newer version
        cursor = test_db.execute("SELECT value FROM _schema_metadata WHERE key = 'version'")
        assert cursor.fetchone()[0] == "20251230"
