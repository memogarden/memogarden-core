"""Tests for auth service module.

Tests password hashing, user CRUD operations, and credential verification.
"""

import pytest
import sqlite3
from memogarden.auth import service
from memogarden.auth.schemas import UserCreate
from memogarden.utils import isodatetime


# ============================================================================
# Password Hashing and Verification Tests
# ============================================================================


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_string(self):
        """Password hashing should return a string."""
        hashed = service.hash_password("SecurePass123")
        assert isinstance(hashed, str)
        assert len(hashed) == 60  # Bcrypt hashes are always 60 characters

    def test_hash_password_different_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        password = "SecurePass123"
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)
        assert hash1 != hash2  # Different salts produce different hashes

    def test_verify_password_valid(self):
        """Verification should succeed for correct password."""
        password = "SecurePass123"
        hashed = service.hash_password(password)
        assert service.verify_password(password, hashed) is True

    def test_verify_password_invalid(self):
        """Verification should fail for incorrect password."""
        password = "SecurePass123"
        wrong_password = "WrongPass456"
        hashed = service.hash_password(password)
        assert service.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_string(self):
        """Verification should fail for empty string."""
        password = "SecurePass123"
        hashed = service.hash_password(password)
        assert service.verify_password("", hashed) is False

    def test_verify_password_unicode(self):
        """Verification should handle unicode characters."""
        password = "SecurePass123🔒"
        hashed = service.hash_password(password)
        assert service.verify_password(password, hashed) is True
        assert service.verify_password("SecurePass123", hashed) is False


# ============================================================================
# User CRUD Operations Tests
# ============================================================================


class TestUserCRUD:
    """Tests for user CRUD operations."""

    def test_create_user_returns_user_response(self, test_db: sqlite3.Connection):
        """Creating a user should return UserResponse with id and metadata."""
        data = UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, data, is_admin=True)

        assert user.id is not None
        assert user.username == "admin"
        assert user.is_admin is True
        assert user.created_at is not None
        # Password hash should not be in response
        assert not hasattr(user, "password_hash")

    def test_create_user_hashes_password(self, test_db: sqlite3.Connection):
        """Password should be hashed, not stored in plain text."""
        data = UserCreate(username="admin", password="SecurePass123")
        service.create_user(test_db, data, is_admin=True)

        # Check database directly
        cursor = test_db.execute("SELECT password_hash FROM users WHERE username = ?", ("admin",))
        row = cursor.fetchone()
        assert row is not None
        password_hash = row["password_hash"]

        # Should be bcrypt hash (60 chars, starts with $2b$)
        assert len(password_hash) == 60
        assert password_hash.startswith("$2b$")

        # Should not be plain text
        assert password_hash != "SecurePass123"

    def test_create_user_creates_entity_entry(self, test_db: sqlite3.Connection):
        """Creating a user should also create an entity registry entry."""
        data = UserCreate(username="admin", password="SecurePass123")
        user = service.create_user(test_db, data, is_admin=True)

        # Check entity exists
        cursor = test_db.execute(
            "SELECT * FROM entity WHERE id = ? AND type = 'users'",
            (user.id,)
        )
        row = cursor.fetchone()
        assert row is not None

    def test_create_user_regular_user(self, test_db: sqlite3.Connection):
        """Creating a regular user (not admin) should work."""
        data = UserCreate(username="user", password="SecurePass123")
        user = service.create_user(test_db, data, is_admin=False)

        assert user.is_admin is False

    def test_create_user_duplicate_username_raises_error(self, test_db: sqlite3.Connection):
        """Creating a user with duplicate username should raise IntegrityError."""
        data = UserCreate(username="admin", password="SecurePass123")
        service.create_user(test_db, data, is_admin=True)

        # Try to create again with same username
        with pytest.raises(sqlite3.IntegrityError):
            service.create_user(test_db, data, is_admin=True)

    def test_create_user_normalizes_username(self, test_db: sqlite3.Connection):
        """Username should be normalized to lowercase."""
        data = UserCreate(username="AdminUser", password="SecurePass123")
        user = service.create_user(test_db, data, is_admin=True)

        assert user.username == "adminuser"

        # Should be retrievable with lowercase
        found = service.get_user_by_username(test_db, "adminuser")
        assert found is not None

    def test_get_user_by_username_found(self, test_db: sqlite3.Connection):
        """Getting user by username should return UserResponse."""
        data = UserCreate(username="admin", password="SecurePass123")
        created = service.create_user(test_db, data, is_admin=True)

        found = service.get_user_by_username(test_db, "admin")
        assert found is not None
        assert found.id == created.id
        assert found.username == "admin"
        assert found.is_admin is True

    def test_get_user_by_username_not_found(self, test_db: sqlite3.Connection):
        """Getting non-existent user should return None."""
        found = service.get_user_by_username(test_db, "nonexistent")
        assert found is None

    def test_get_user_by_username_case_insensitive(self, test_db: sqlite3.Connection):
        """Username lookup should be case-insensitive."""
        data = UserCreate(username="admin", password="SecurePass123")
        created = service.create_user(test_db, data, is_admin=True)

        # Try different cases
        found1 = service.get_user_by_username(test_db, "admin")
        found2 = service.get_user_by_username(test_db, "ADMIN")
        found3 = service.get_user_by_username(test_db, "Admin")

        assert found1 is not None
        assert found2 is not None
        assert found3 is not None
        assert found1.id == created.id
        assert found2.id == created.id
        assert found3.id == created.id

    def test_get_user_with_password_returns_tuple(self, test_db: sqlite3.Connection):
        """Getting user with password should return (UserResponse, password_hash)."""
        data = UserCreate(username="admin", password="SecurePass123")
        created = service.create_user(test_db, data, is_admin=True)

        result = service.get_user_with_password(test_db, "admin")
        assert result is not None

        user, password_hash = result
        assert user.id == created.id
        assert user.username == "admin"
        assert isinstance(password_hash, str)
        assert len(password_hash) == 60

    def test_get_user_with_password_not_found(self, test_db: sqlite3.Connection):
        """Getting non-existent user with password should return None."""
        result = service.get_user_with_password(test_db, "nonexistent")
        assert result is None

    def test_get_user_by_id_found(self, test_db: sqlite3.Connection):
        """Getting user by ID should return UserResponse."""
        data = UserCreate(username="admin", password="SecurePass123")
        created = service.create_user(test_db, data, is_admin=True)

        found = service.get_user_by_id(test_db, created.id)
        assert found is not None
        assert found.id == created.id
        assert found.username == "admin"

    def test_get_user_by_id_not_found(self, test_db: sqlite3.Connection):
        """Getting non-existent user by ID should return None."""
        found = service.get_user_by_id(test_db, "550e8400-e29b-41d4-a716-446655440000")
        assert found is None

    def test_count_users_empty_database(self, test_db: sqlite3.Connection):
        """Counting users in empty database should return 0."""
        count = service.count_users(test_db)
        assert count == 0

    def test_count_users_multiple_users(self, test_db: sqlite3.Connection):
        """Counting users should return correct count."""
        service.create_user(test_db, UserCreate(username="user1", password="Pass1234"), is_admin=False)
        service.create_user(test_db, UserCreate(username="user2", password="Pass4567"), is_admin=False)
        service.create_user(test_db, UserCreate(username="admin", password="Pass7890"), is_admin=True)

        count = service.count_users(test_db)
        assert count == 3

    def test_has_admin_user_no_users(self, test_db: sqlite3.Connection):
        """has_admin_user should return False when no users exist."""
        assert service.has_admin_user(test_db) is False

    def test_has_admin_user_only_regular_users(self, test_db: sqlite3.Connection):
        """has_admin_user should return False when only regular users exist."""
        service.create_user(test_db, UserCreate(username="user1", password="Pass1234"), is_admin=False)
        service.create_user(test_db, UserCreate(username="user2", password="Pass4567"), is_admin=False)

        assert service.has_admin_user(test_db) is False

    def test_has_admin_user_with_admin(self, test_db: sqlite3.Connection):
        """has_admin_user should return True when admin exists."""
        service.create_user(test_db, UserCreate(username="user1", password="Pass1234"), is_admin=False)
        service.create_user(test_db, UserCreate(username="admin", password="Pass4567"), is_admin=True)

        assert service.has_admin_user(test_db) is True


# ============================================================================
# Authentication Verification Tests
# ============================================================================


class TestCredentialVerification:
    """Tests for credential verification."""

    def test_verify_credentials_valid(self, test_db: sqlite3.Connection):
        """Valid credentials should return user."""
        data = UserCreate(username="admin", password="SecurePass123")
        created = service.create_user(test_db, data, is_admin=True)

        user = service.verify_credentials(test_db, "admin", "SecurePass123")
        assert user is not None
        assert user.id == created.id
        assert user.username == "admin"

    def test_verify_credentials_invalid_password(self, test_db: sqlite3.Connection):
        """Invalid password should return None."""
        data = UserCreate(username="admin", password="SecurePass123")
        service.create_user(test_db, data, is_admin=True)

        user = service.verify_credentials(test_db, "admin", "WrongPassword")
        assert user is None

    def test_verify_credentials_invalid_username(self, test_db: sqlite3.Connection):
        """Invalid username should return None."""
        data = UserCreate(username="admin", password="SecurePass123")
        service.create_user(test_db, data, is_admin=True)

        user = service.verify_credentials(test_db, "nonexistent", "SecurePass123")
        assert user is None

    def test_verify_credentials_case_insensitive_username(self, test_db: sqlite3.Connection):
        """Username verification should be case-insensitive."""
        data = UserCreate(username="admin", password="SecurePass123")
        created = service.create_user(test_db, data, is_admin=True)

        # Try different cases
        user1 = service.verify_credentials(test_db, "admin", "SecurePass123")
        user2 = service.verify_credentials(test_db, "ADMIN", "SecurePass123")
        user3 = service.verify_credentials(test_db, "Admin", "SecurePass123")

        assert user1 is not None
        assert user2 is not None
        assert user3 is not None
        assert user1.id == created.id
        assert user2.id == created.id
        assert user3.id == created.id

    def test_verify_credentials_password_case_sensitive(self, test_db: sqlite3.Connection):
        """Password verification should be case-sensitive."""
        data = UserCreate(username="admin", password="SecurePass123")
        service.create_user(test_db, data, is_admin=True)

        # Lowercase should not match
        user = service.verify_credentials(test_db, "admin", "securepass123")
        assert user is None

        # Exact case should match
        user = service.verify_credentials(test_db, "admin", "SecurePass123")
        assert user is not None
