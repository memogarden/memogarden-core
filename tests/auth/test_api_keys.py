"""Tests for API key service module.

Tests API key generation, hashing, CRUD operations, and verification.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta

from memogarden.auth import api_keys as api_keys_service
from memogarden.auth.schemas import APIKeyCreate
from memogarden.utils import isodatetime


# ============================================================================
# API Key Generation Tests
# ============================================================================


class TestAPIKeyGeneration:
    """Tests for API key generation."""

    def test_generate_api_key_returns_string(self):
        """API key generation should return a string."""
        key = api_keys_service.generate_api_key()
        assert isinstance(key, str)
        assert len(key) == 76  # "mg_sk_agent_" (12) + 64 hex chars

    def test_generate_api_key_has_correct_prefix(self):
        """API key should have the correct prefix."""
        key = api_keys_service.generate_api_key()
        assert key.startswith("mg_sk_agent_")

    def test_generate_api_keys_are_unique(self):
        """Each generated API key should be unique."""
        key1 = api_keys_service.generate_api_key()
        key2 = api_keys_service.generate_api_key()
        assert key1 != key2

    def test_get_api_key_prefix(self):
        """Extracting prefix should return first 12 characters."""
        key = "mg_sk_agent_abc123def456789"
        prefix = api_keys_service.get_api_key_prefix(key)
        assert prefix == "mg_sk_agent_"

    def test_hash_api_key_returns_hash(self):
        """Hashing an API key should return a bcrypt hash."""
        key = api_keys_service.generate_api_key()
        hashed = api_keys_service.hash_api_key(key)
        assert isinstance(hashed, str)
        assert len(hashed) == 60  # Bcrypt hashes are always 60 characters
        assert hashed.startswith("$2b$")

    def test_verify_api_key_valid(self):
        """Verification should succeed for correct API key."""
        key = api_keys_service.generate_api_key()
        hashed = api_keys_service.hash_api_key(key)
        assert api_keys_service.verify_api_key(key, hashed) is True

    def test_verify_api_key_invalid(self):
        """Verification should fail for incorrect API key."""
        key1 = api_keys_service.generate_api_key()
        key2 = api_keys_service.generate_api_key()
        hashed = api_keys_service.hash_api_key(key1)
        assert api_keys_service.verify_api_key(key2, hashed) is False


# ============================================================================
# API Key CRUD Operations Tests
# ============================================================================


class TestAPIKeyCRUD:
    """Tests for API key CRUD operations."""

    def test_create_api_key_returns_response(self, test_db: sqlite3.Connection):
        """Creating an API key should return APIKeyResponse."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key = api_keys_service.create_api_key(test_db, user.id, data)

        assert api_key.id is not None
        assert api_key.name == "test-key"
        assert api_key.key is not None  # Full key shown on creation
        assert api_key.prefix == "mg_sk_agent_"
        assert api_key.expires_at is None
        assert api_key.created_at is not None
        assert api_key.last_seen is None
        assert api_key.revoked_at is None

    def test_create_api_key_hashes_key(self, test_db: sqlite3.Connection):
        """API key should be hashed, not stored in plain text."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key_response = api_keys_service.create_api_key(test_db, user.id, data)

        # Check database directly
        cursor = test_db.execute("SELECT key_hash FROM api_keys WHERE id = ?", (api_key_response.id,))
        row = cursor.fetchone()
        assert row is not None
        key_hash = row["key_hash"]

        # Should be bcrypt hash (60 chars, starts with $2b$)
        assert len(key_hash) == 60
        assert key_hash.startswith("$2b$")

        # Should not be plain text
        assert key_hash != api_key_response.key

    def test_create_api_key_stores_prefix(self, test_db: sqlite3.Connection):
        """API key prefix should be stored separately for display."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key = api_keys_service.create_api_key(test_db, user.id, data)

        # Check prefix is stored
        cursor = test_db.execute("SELECT key_prefix FROM api_keys WHERE id = ?", (api_key.id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["key_prefix"] == "mg_sk_agent_"

    def test_create_api_key_with_expiration(self, test_db: sqlite3.Connection):
        """Creating an API key with expiration should set expires_at."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        expires_at = datetime(2026, 12, 31, 23, 59, 59)
        data = APIKeyCreate(name="test-key", expires_at=expires_at)
        api_key = api_keys_service.create_api_key(test_db, user.id, data)

        assert api_key.expires_at is not None

    def test_list_api_keys_empty(self, test_db: sqlite3.Connection):
        """Listing API keys for user with no keys should return empty list."""
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        api_keys = api_keys_service.list_api_keys(test_db, user.id)
        assert api_keys == []

    def test_list_api_keys_returns_keys(self, test_db: sqlite3.Connection):
        """Listing API keys should return all keys for user (without full keys)."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        # Create multiple API keys
        data1 = APIKeyCreate(name="key1", expires_at=None)
        data2 = APIKeyCreate(name="key2", expires_at=None)
        api_keys_service.create_api_key(test_db, user.id, data1)
        api_keys_service.create_api_key(test_db, user.id, data2)

        # List API keys
        api_keys = api_keys_service.list_api_keys(test_db, user.id)
        assert len(api_keys) == 2

        # Verify full keys are not included
        for api_key in api_keys:
            assert not hasattr(api_key, 'key')  # No full key in list
            assert api_key.prefix == "mg_sk_agent_"

    def test_list_api_keys_excludes_other_users(self, test_db: sqlite3.Connection):
        """Listing API keys should only show keys for specified user."""
        # Create two users
        from memogarden.auth import service
        user1_data = service.UserCreate(username="user1", password="Pass1234")
        user2_data = service.UserCreate(username="user2", password="Pass5678")
        user1 = service.create_user(test_db, user1_data, is_admin=False)
        user2 = service.create_user(test_db, user2_data, is_admin=False)

        # Create API keys for user1
        data1 = APIKeyCreate(name="user1-key", expires_at=None)
        api_keys_service.create_api_key(test_db, user1.id, data1)

        # Create API keys for user2
        data2 = APIKeyCreate(name="user2-key", expires_at=None)
        api_keys_service.create_api_key(test_db, user2.id, data2)

        # List user1's keys
        user1_keys = api_keys_service.list_api_keys(test_db, user1.id)
        assert len(user1_keys) == 1
        assert user1_keys[0].name == "user1-key"

        # List user2's keys
        user2_keys = api_keys_service.list_api_keys(test_db, user2.id)
        assert len(user2_keys) == 1
        assert user2_keys[0].name == "user2-key"

    def test_revoke_api_key_sets_revoked_at(self, test_db: sqlite3.Connection):
        """Revoking an API key should set revoked_at timestamp."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key = api_keys_service.create_api_key(test_db, user.id, data)

        # Revoke the API key
        success = api_keys_service.revoke_api_key(test_db, api_key.id, user.id)
        assert success is True

        # Check revoked_at is set
        revoked_key = api_keys_service.get_api_key_by_id(test_db, api_key.id)
        assert revoked_key is not None
        assert revoked_key.revoked_at is not None

    def test_revoke_api_key_only_for_owner(self, test_db: sqlite3.Connection):
        """Revoking an API key should only work for the owner."""
        # Create two users
        from memogarden.auth import service
        user1_data = service.UserCreate(username="user1", password="Pass1234")
        user2_data = service.UserCreate(username="user2", password="Pass5678")
        user1 = service.create_user(test_db, user1_data, is_admin=False)
        user2 = service.create_user(test_db, user2_data, is_admin=False)

        # Create API key for user1
        data = APIKeyCreate(name="user1-key", expires_at=None)
        api_key = api_keys_service.create_api_key(test_db, user1.id, data)

        # Try to revoke as user2 (should fail)
        success = api_keys_service.revoke_api_key(test_db, api_key.id, user2.id)
        assert success is False

        # Verify key is still active
        active_key = api_keys_service.get_api_key_by_id(test_db, api_key.id)
        assert active_key.revoked_at is None

    def test_revoke_api_key_idempotent(self, test_db: sqlite3.Connection):
        """Revoking an already revoked key should return False."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key = api_keys_service.create_api_key(test_db, user.id, data)

        # Revoke once
        success1 = api_keys_service.revoke_api_key(test_db, api_key.id, user.id)
        assert success1 is True

        # Try to revoke again
        success2 = api_keys_service.revoke_api_key(test_db, api_key.id, user.id)
        assert success2 is False

    def test_get_api_key_by_id_found(self, test_db: sqlite3.Connection):
        """Getting an API key by ID should return the key (without full key)."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        data = APIKeyCreate(name="test-key", expires_at=None)
        created_key = api_keys_service.create_api_key(test_db, user.id, data)

        # Get by ID
        api_key = api_keys_service.get_api_key_by_id(test_db, created_key.id)
        assert api_key is not None
        assert api_key.id == created_key.id
        assert api_key.name == "test-key"
        assert not hasattr(api_key, 'key')  # No full key in get_by_id
        assert api_key.prefix == "mg_sk_agent_"

    def test_get_api_key_by_id_not_found(self, test_db: sqlite3.Connection):
        """Getting a non-existent API key should return None."""
        api_key = api_keys_service.get_api_key_by_id(test_db, "550e8400-e29b-41d4-a716-446655440000")
        assert api_key is None


# ============================================================================
# API Key Authentication Tests
# ============================================================================


class TestAPIKeyAuthentication:
    """Tests for API key authentication."""

    def test_verify_api_key_and_get_user_valid(self, test_db: sqlite3.Connection):
        """Verifying a valid API key should return user and key ID."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        # Create API key
        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key_response = api_keys_service.create_api_key(test_db, user.id, data)
        plain_key = api_key_response.key

        # Verify the key
        result = api_keys_service.verify_api_key_and_get_user(test_db, plain_key)
        assert result is not None
        returned_user_id, returned_api_key_id = result
        assert returned_user_id == user.id
        assert returned_api_key_id == api_key_response.id

    def test_verify_api_key_and_get_user_invalid(self, test_db: sqlite3.Connection):
        """Verifying an invalid API key should return None."""
        result = api_keys_service.verify_api_key_and_get_user(test_db, "mg_sk_agent_invalid")
        assert result is None

    def test_verify_api_key_updates_last_seen(self, test_db: sqlite3.Connection):
        """Verifying an API key should update last_seen timestamp."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        # Create API key
        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key_response = api_keys_service.create_api_key(test_db, user.id, data)
        plain_key = api_key_response.key

        # Verify last_seen is None initially
        api_key = api_keys_service.get_api_key_by_id(test_db, api_key_response.id)
        assert api_key.last_seen is None

        # Verify the key (should update last_seen)
        result = api_keys_service.verify_api_key_and_get_user(test_db, plain_key)
        assert result is not None

        # Check last_seen was updated
        updated_key = api_keys_service.get_api_key_by_id(test_db, api_key_response.id)
        assert updated_key.last_seen is not None

    def test_verify_api_key_revoked_key_fails(self, test_db: sqlite3.Connection):
        """Verifying a revoked API key should return None."""
        # First create a user
        from memogarden.auth import service
        user_data = service.UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, user_data, is_admin=True)

        # Create and revoke API key
        data = APIKeyCreate(name="test-key", expires_at=None)
        api_key_response = api_keys_service.create_api_key(test_db, user.id, data)
        plain_key = api_key_response.key
        api_keys_service.revoke_api_key(test_db, api_key_response.id, user.id)

        # Try to verify revoked key
        result = api_keys_service.verify_api_key_and_get_user(test_db, plain_key)
        assert result is None
