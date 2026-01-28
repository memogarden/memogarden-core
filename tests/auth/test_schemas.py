"""
Tests for Authentication Pydantic schemas (API validation).

Tests verify that:
- User schemas validate data correctly (registration, login, response)
- API key schemas validate data correctly (create, list, response)
- JWT token schemas work correctly
- Password validation requirements are enforced
- Field types and constraints are enforced
- Optional fields work as expected
- Serialization/deserialization works properly
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from memogarden.auth.schemas import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    APIKeyBase,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    TokenPayload,
    TokenResponse,
    AdminRegistrationResponse,
)


# ============================================================================
# User Schemas Tests
# ============================================================================


class TestUserCreate:
    """Tests for UserCreate schema (admin registration)."""

    def test_create_with_valid_data(self):
        """Test creating a user with valid data."""
        data = {
            "username": "admin",
            "password": "SecurePass123",
        }
        user = UserCreate(**data)

        assert user.username == "admin"
        assert user.password == "SecurePass123"

    def test_username_normalized_to_lowercase(self):
        """Test that username is normalized to lowercase."""
        data = {
            "username": "AdminUser",
            "password": "SecurePass123",
        }
        user = UserCreate(**data)
        assert user.username == "adminuser"

    def test_password_min_length_enforced(self):
        """Test that password minimum length of 8 is enforced."""
        data = {
            "username": "admin",
            "password": "Short1",  # Only 7 characters
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)

        errors = exc_info.value.errors()
        assert any("at least 8 characters" in str(err["msg"]).lower() for err in errors)

    def test_password_requires_letter(self):
        """Test that password must contain at least one letter."""
        data = {
            "username": "admin",
            "password": "12345678",  # No letters
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)

        errors = exc_info.value.errors()
        assert any("must contain at least one letter" in str(err["msg"]).lower() for err in errors)

    def test_password_requires_digit(self):
        """Test that password must contain at least one digit."""
        data = {
            "username": "admin",
            "password": "PasswordOnly",  # No digits
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)

        errors = exc_info.value.errors()
        assert any("must contain at least one digit" in str(err["msg"]).lower() for err in errors)

    def test_username_only_allows_alphanumeric_hyphen_underscore(self):
        """Test that username only allows alphanumeric characters, hyphens, and underscores."""
        invalid_usernames = [
            "admin@user",  # @ not allowed
            "admin user",  # space not allowed
            "admin.user",  # dot not allowed
            "admin#user",  # # not allowed
        ]

        for invalid_username in invalid_usernames:
            data = {
                "username": invalid_username,
                "password": "SecurePass123",
            }
            with pytest.raises(ValidationError):
                UserCreate(**data)

    def test_username_with_valid_special_chars(self):
        """Test that underscores and hyphens are allowed in username."""
        valid_usernames = [
            "admin_user",
            "admin-user",
            "admin_123",
            "admin-456",
        ]

        for valid_username in valid_usernames:
            data = {
                "username": valid_username,
                "password": "SecurePass123",
            }
            user = UserCreate(**data)
            assert user.username == valid_username.lower()

    def test_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        # Missing password
        data = {"username": "admin"}
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "password" in error_fields

    def test_password_with_special_characters(self):
        """Test that passwords with special characters are accepted."""
        data = {
            "username": "admin",
            "password": "Secure@Pass#123!",
        }
        user = UserCreate(**data)
        assert user.password == "Secure@Pass#123!"


class TestUserLogin:
    """Tests for UserLogin schema."""

    def test_login_with_valid_credentials(self):
        """Test login schema with valid credentials."""
        data = {
            "username": "admin",
            "password": "SecurePass123",
        }
        login = UserLogin(**data)

        assert login.username == "admin"
        assert login.password == "SecurePass123"

    def test_login_missing_username(self):
        """Test that missing username raises validation error."""
        data = {"password": "SecurePass123"}
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**data)

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "username" in error_fields

    def test_login_missing_password(self):
        """Test that missing password raises validation error."""
        data = {"username": "admin"}
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(**data)

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "password" in error_fields


class TestUserResponse:
    """Tests for UserResponse schema."""

    def test_response_with_all_fields(self):
        """Test response schema with all fields."""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "admin",
            "is_admin": True,
            "created_at": "2025-12-29T10:30:00Z",
        }
        user = UserResponse(**data)

        assert user.id == "550e8400-e29b-41d4-a716-446655440000"
        assert user.username == "admin"
        assert user.is_admin is True
        assert user.created_at == datetime.fromisoformat("2025-12-29T10:30:00+00:00")

    def test_response_for_regular_user(self):
        """Test response for a non-admin user."""
        data = {
            "id": "user-id-123",
            "username": "regularuser",
            "is_admin": False,
            "created_at": "2025-12-29T10:30:00Z",
        }
        user = UserResponse(**data)

        assert user.is_admin is False
        assert user.username == "regularuser"

    def test_response_serialization(self):
        """Test that response can be serialized to JSON."""
        data = {
            "id": "test-id",
            "username": "admin",
            "is_admin": True,
            "created_at": "2025-12-29T10:30:00Z",
        }
        user = UserResponse(**data)

        # Test dict serialization
        json_dict = user.model_dump()
        assert json_dict["id"] == "test-id"
        assert json_dict["username"] == "admin"
        assert json_dict["is_admin"] is True

        # Test JSON mode
        json_str = user.model_dump_json()
        assert "test-id" in json_str
        assert "admin" in json_str


class TestUserBase:
    """Tests for UserBase schema."""

    def test_base_shared_fields(self):
        """Test that base schema has username field."""
        data = {"username": "testuser"}
        user = UserBase(**data)

        assert user.username == "testuser"


# ============================================================================
# API Key Schemas Tests
# ============================================================================


class TestAPIKeyCreate:
    """Tests for APIKeyCreate schema."""

    def test_create_with_name_only(self):
        """Test creating API key with just name (no expiry)."""
        data = {
            "name": "claude-code",
        }
        api_key = APIKeyCreate(**data)

        assert api_key.name == "claude-code"
        assert api_key.expires_at is None

    def test_create_with_expiry(self):
        """Test creating API key with expiration date."""
        data = {
            "name": "temp-script",
            "expires_at": "2026-12-31T23:59:59Z",
        }
        api_key = APIKeyCreate(**data)

        assert api_key.name == "temp-script"
        assert api_key.expires_at == datetime.fromisoformat("2026-12-31T23:59:59+00:00")

    def test_create_missing_name(self):
        """Test that missing name raises validation error."""
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreate(**data)

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "name" in error_fields

    def test_name_min_length(self):
        """Test that name minimum length is enforced."""
        data = {"name": ""}  # Empty string
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreate(**data)

        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(err["msg"]).lower() for err in errors)

    def test_name_max_length(self):
        """Test that name maximum length is enforced."""
        data = {"name": "a" * 101}  # 101 characters (max is 100)
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreate(**data)

        errors = exc_info.value.errors()
        assert any("at most 100 characters" in str(err["msg"]).lower() for err in errors)


class TestAPIKeyResponse:
    """Tests for APIKeyResponse schema."""

    def test_response_with_full_key(self):
        """Test response when full key is included (on creation)."""
        data = {
            "id": "660e8400-e29b-41d4-a716-446655440000",
            "name": "claude-code",
            "key": "mg_sk_agent_abc123def456...",
            "prefix": "mg_sk_agent_",
            "expires_at": "2026-12-31T23:59:59Z",
            "created_at": "2025-12-29T10:30:00Z",
            "last_seen": None,
            "revoked_at": None,
        }
        api_key = APIKeyResponse(**data)

        assert api_key.id == "660e8400-e29b-41d4-a716-446655440000"
        assert api_key.name == "claude-code"
        assert api_key.key == "mg_sk_agent_abc123def456..."
        assert api_key.prefix == "mg_sk_agent_"
        assert api_key.expires_at == datetime.fromisoformat("2026-12-31T23:59:59+00:00")
        assert api_key.last_seen is None
        assert api_key.revoked_at is None

    def test_response_without_full_key(self):
        """Test response when full key is None (list operations)."""
        data = {
            "id": "key-id-123",
            "name": "custom-script",
            "key": None,
            "prefix": "mg_sk_agent_",
            "expires_at": None,
            "created_at": "2025-12-29T10:30:00Z",
            "last_seen": "2025-12-29T15:45:00Z",
            "revoked_at": None,
        }
        api_key = APIKeyResponse(**data)

        assert api_key.key is None
        assert api_key.last_seen == datetime.fromisoformat("2025-12-29T15:45:00+00:00")

    def test_response_with_revoked_key(self):
        """Test response for a revoked API key."""
        data = {
            "id": "revoked-key-id",
            "name": "old-script",
            "key": None,
            "prefix": "mg_sk_agent_",
            "expires_at": None,
            "created_at": "2025-12-29T10:30:00Z",
            "last_seen": "2025-12-29T15:45:00Z",
            "revoked_at": "2025-12-30T10:00:00Z",
        }
        api_key = APIKeyResponse(**data)

        assert api_key.revoked_at == datetime.fromisoformat("2025-12-30T10:00:00+00:00")


class TestAPIKeyListResponse:
    """Tests for APIKeyListResponse schema."""

    def test_list_response_does_not_have_full_key(self):
        """Test that list response schema does not include full key field."""
        # This schema is designed to never include the full key
        data = {
            "id": "key-id-123",
            "name": "custom-script",
            "prefix": "mg_sk_agent_",
            "expires_at": None,
            "created_at": "2025-12-29T10:30:00Z",
            "last_seen": None,
            "revoked_at": None,
        }
        api_key = APIKeyListResponse(**data)

        assert api_key.id == "key-id-123"
        assert api_key.name == "custom-script"
        assert api_key.prefix == "mg_sk_agent_"
        # No 'key' field in this schema

    def test_list_response_serialization(self):
        """Test that list response can be serialized to JSON."""
        data = {
            "id": "test-key-id",
            "name": "test-script",
            "prefix": "mg_sk_agent_",
            "expires_at": "2026-12-31T23:59:59Z",
            "created_at": "2025-12-29T10:30:00Z",
            "last_seen": None,
            "revoked_at": None,
        }
        api_key = APIKeyListResponse(**data)

        json_dict = api_key.model_dump()
        assert json_dict["id"] == "test-key-id"
        assert json_dict["name"] == "test-script"
        assert "key" not in json_dict  # Should not have full key


class TestAPIKeyBase:
    """Tests for APIKeyBase schema."""

    def test_base_shared_fields(self):
        """Test that base schema has name field."""
        data = {"name": "test-key"}
        api_key = APIKeyBase(**data)

        assert api_key.name == "test-key"


# ============================================================================
# JWT Token Schemas Tests
# ============================================================================


class TestTokenPayload:
    """Tests for TokenPayload schema (internal JWT token claims)."""

    def test_payload_with_all_fields(self):
        """Test token payload with all required fields."""
        data = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "username": "admin",
            "is_admin": True,
            "exp": 1735689600,  # Unix timestamp
            "iat": 1735689600,
        }
        payload = TokenPayload(**data)

        assert payload.sub == "550e8400-e29b-41d4-a716-446655440000"
        assert payload.username == "admin"
        assert payload.is_admin is True
        assert payload.exp == 1735689600
        assert payload.iat == 1735689600

    def test_payload_for_regular_user(self):
        """Test token payload for non-admin user."""
        data = {
            "sub": "user-id-123",
            "username": "regularuser",
            "is_admin": False,
            "exp": 1735689600,
            "iat": 1735689600,
        }
        payload = TokenPayload(**data)

        assert payload.is_admin is False
        assert payload.username == "regularuser"


class TestTokenResponse:
    """Tests for TokenResponse schema."""

    def test_response_with_all_fields(self):
        """Test token response with access token and user info."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "admin",
                "is_admin": True,
                "created_at": "2025-12-29T10:30:00Z",
            },
        }
        response = TokenResponse(**data)

        assert response.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert response.token_type == "bearer"
        assert response.user.id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.user.username == "admin"
        assert response.user.is_admin is True

    def test_response_default_token_type(self):
        """Test that token_type defaults to 'bearer'."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user": {
                "id": "user-id-123",
                "username": "admin",
                "is_admin": True,
                "created_at": "2025-12-29T10:30:00Z",
            },
        }
        response = TokenResponse(**data)

        assert response.token_type == "bearer"


class TestAdminRegistrationResponse:
    """Tests for AdminRegistrationResponse schema."""

    def test_response_with_message_and_user(self):
        """Test admin registration response with success message and user."""
        data = {
            "message": "Admin account created successfully",
            "user": {
                "id": "admin-id-123",
                "username": "admin",
                "is_admin": True,
                "created_at": "2025-12-29T10:30:00Z",
            },
        }
        response = AdminRegistrationResponse(**data)

        assert response.message == "Admin account created successfully"
        assert response.user.id == "admin-id-123"
        assert response.user.username == "admin"
        assert response.user.is_admin is True
