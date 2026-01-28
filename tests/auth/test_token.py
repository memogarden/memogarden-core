"""
Tests for JWT Token Service.

Tests verify that:
- Tokens are generated with correct claims (sub, username, is_admin, iat, exp)
- Tokens are validated and decoded correctly
- Expired tokens are rejected
- Invalid tokens are rejected
- Token expiry introspection works correctly
- Token generation uses configured expiry duration
"""

import pytest
import jwt as pyjwt
from datetime import datetime, timedelta

from memogarden.auth.token import (
    generate_access_token,
    validate_access_token,
    decode_token_no_validation,
    get_token_expiry_remaining,
    is_token_expired,
)
from memogarden.auth.schemas import UserResponse
from memogarden.utils import isodatetime


# ============================================================================
# Token Generation Tests
# ============================================================================


class TestGenerateAccessToken:
    """Tests for generate_access_token function."""

    def test_generate_token_with_valid_user(self):
        """Test token generation with valid user data."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)

        assert isinstance(token, str)
        assert len(token) > 0  # JWT tokens are non-empty strings

    def test_token_contains_required_claims(self):
        """Test that generated token contains all required claims."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=True,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)

        # Decode without validation to inspect claims
        payload = pyjwt.decode(token, options={"verify_signature": False})

        assert payload["sub"] == user.id
        assert payload["username"] == user.username
        assert payload["is_admin"] == user.is_admin
        assert "iat" in payload
        assert "exp" in payload
        assert isinstance(payload["iat"], int)
        assert isinstance(payload["exp"], int)

    def test_token_expiry_is_future_timestamp(self):
        """Test that token expiry is set to a future timestamp."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)
        payload = pyjwt.decode(token, options={"verify_signature": False})

        now = isodatetime.now_unix()
        exp = payload["exp"]

        # Expiry should be in the future (within 31 days to account for test timing)
        assert exp > now
        assert exp < now + (31 * 24 * 60 * 60)  # Less than 31 days

    def test_token_issued_at_is_current_time(self):
        """Test that token iat is close to current time."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        before = isodatetime.now_unix()
        token = generate_access_token(user)
        after = isodatetime.now_unix()

        payload = pyjwt.decode(token, options={"verify_signature": False})
        iat_ts = payload["iat"]

        # Compare timestamps directly (iat is integer, may have second precision)
        # Allow for 2 second tolerance to account for timestamp rounding
        assert before - 2 <= iat_ts <= after + 2

    def test_token_uses_configured_secret_key(self):
        """Test that token is signed with configured secret key."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)

        # Should not raise DecodeError if secret key is correct
        payload = pyjwt.decode(
            token,
            "change-me-in-production-use-env-var",
            algorithms=["HS256"],
        )

        assert payload["sub"] == user.id


# ============================================================================
# Token Validation Tests
# ============================================================================


class TestValidateAccessToken:
    """Tests for validate_access_token function."""

    def test_validate_valid_token(self):
        """Test validating a valid token."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)
        payload = validate_access_token(token)

        assert payload.sub == user.id
        assert payload.username == user.username
        assert payload.is_admin == user.is_admin
        assert isinstance(payload.exp, int)
        assert isinstance(payload.iat, int)

    def test_validate_token_with_wrong_secret_raises_error(self):
        """Test that token with wrong secret raises InvalidTokenError."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)

        # Manually decode and re-encode with different secret
        payload = pyjwt.decode(token, options={"verify_signature": False})
        forged_token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(pyjwt.InvalidTokenError):
            validate_access_token(forged_token)

    def test_validate_expired_token_raises_error(self):
        """Test that expired token raises ExpiredSignatureError."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        # Create token that expired 1 hour ago
        past_ts = isodatetime.now_unix() - (60 * 60)  # 1 hour ago
        iat_ts = past_ts - (30 * 24 * 60 * 60)  # 30 days before that
        payload = {
            "sub": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "iat": iat_ts,
            "exp": past_ts,
        }

        expired_token = pyjwt.encode(
            payload,
            "change-me-in-production-use-env-var",
            algorithm="HS256",
        )

        with pytest.raises(pyjwt.ExpiredSignatureError):
            validate_access_token(expired_token)

    def test_validate_malformed_token_raises_error(self):
        """Test that malformed token raises DecodeError."""
        malformed_tokens = [
            "not-a-jwt",
            "invalid.token.here",
            "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIn0.",  # None algorithm
            "",
        ]

        for token in malformed_tokens:
            with pytest.raises(pyjwt.InvalidTokenError):
                validate_access_token(token)

    def test_validate_token_without_required_claims_raises_error(self):
        """Test that token missing required claims raises error."""
        # Token with only 'sub' claim
        payload = {"sub": "550e8400-e29b-41d4-a716-446655440000"}
        incomplete_token = pyjwt.encode(
            payload,
            "change-me-in-production-use-env-var",
            algorithm="HS256",
        )

        with pytest.raises(pyjwt.InvalidTokenError):
            validate_access_token(incomplete_token)

    def test_validate_admin_token_preserves_admin_status(self):
        """Test that admin status is correctly validated."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="admin",
            is_admin=True,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)
        payload = validate_access_token(token)

        assert payload.is_admin is True


# ============================================================================
# Token Introspection Tests
# ============================================================================


class TestGetTokenExpiryRemaining:
    """Tests for get_token_expiry_remaining function."""

    def test_get_remaining_time_for_valid_token(self):
        """Test getting remaining time for a valid token."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)
        remaining = get_token_expiry_remaining(token)

        assert remaining is not None
        assert isinstance(remaining, timedelta)

        # Should be approximately 30 days (allowing 1 minute tolerance)
        expected_days = 30
        actual_days = remaining.total_seconds() / (24 * 60 * 60)
        assert expected_days - 0.001 < actual_days < expected_days + 0.001

    def test_get_remaining_time_for_expired_token_returns_none(self):
        """Test that expired token returns None."""
        # Create expired token
        past_ts = isodatetime.now_unix() - (60 * 60)  # 1 hour ago
        iat_ts = past_ts - (30 * 24 * 60 * 60)  # 30 days before that
        payload = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "username": "testuser",
            "is_admin": False,
            "iat": iat_ts,
            "exp": past_ts,
        }

        expired_token = pyjwt.encode(
            payload,
            "change-me-in-production-use-env-var",
            algorithm="HS256",
        )

        remaining = get_token_expiry_remaining(expired_token)
        assert remaining is None

    def test_get_remaining_time_for_invalid_token_returns_none(self):
        """Test that invalid token returns None."""
        remaining = get_token_expiry_remaining("invalid-token")
        assert remaining is None


class TestIsTokenExpired:
    """Tests for is_token_expired function."""

    def test_valid_token_returns_false(self):
        """Test that valid token returns False (not expired)."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)
        assert is_token_expired(token) is False

    def test_expired_token_returns_true(self):
        """Test that expired token returns True."""
        past_ts = isodatetime.now_unix() - (60 * 60)  # 1 hour ago
        iat_ts = past_ts - (30 * 24 * 60 * 60)  # 30 days before that
        payload = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "username": "testuser",
            "is_admin": False,
            "iat": iat_ts,
            "exp": past_ts,
        }

        expired_token = pyjwt.encode(
            payload,
            "change-me-in-production-use-env-var",
            algorithm="HS256",
        )

        assert is_token_expired(expired_token) is True

    def test_invalid_token_returns_true(self):
        """Test that invalid token returns True (treated as expired)."""
        assert is_token_expired("invalid-token") is True
        assert is_token_expired("") is True


class TestDecodeTokenNoValidation:
    """Tests for decode_token_no_validation function."""

    def test_decode_without_verification(self):
        """Test decoding token without signature verification."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            username="testuser",
            is_admin=False,
            created_at=datetime(2025, 12, 29, 10, 30, 0),
        )

        token = generate_access_token(user)
        payload = decode_token_no_validation(token)

        assert isinstance(payload, dict)
        assert payload["sub"] == user.id
        assert payload["username"] == user.username

    def test_decode_forged_token_succeeds_without_verification(self):
        """Test that forged token can be decoded without verification."""
        now_ts = isodatetime.now_unix()
        payload_dict = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "username": "testuser",
            "is_admin": True,  # Forged admin status
            "iat": now_ts,
            "exp": now_ts + (30 * 24 * 60 * 60),
        }

        forged_token = pyjwt.encode(payload_dict, "wrong-secret", algorithm="HS256")

        # Should succeed even though signature is wrong
        payload = decode_token_no_validation(forged_token)

        assert payload["username"] == "testuser"
        assert payload["is_admin"] is True  # Forged claim is visible
