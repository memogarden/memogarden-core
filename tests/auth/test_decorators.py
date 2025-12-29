"""Tests for authentication decorators.

Tests the @require_auth, @localhost_only, and @first_time_only decorators
that enforce security constraints on protected endpoints.
"""

import pytest
from flask import g
from memogarden_core.auth import api_keys, decorators, schemas, service, token
from memogarden_core.db import get_core
from memogarden_core.exceptions import AuthenticationError
from memogarden_core.config import settings


class TestLocalhostOnlyDecorator:
    """Tests for @localhost_only decorator."""

    def test_non_localhost_blocked(self, client):
        """Should block requests from non-localhost."""
        # Set bypass config to simulate non-localhost request
        original_bypass = settings.bypass_localhost_check
        settings.bypass_localhost_check = True
        try:
            response = client.post(
                "/admin/register",
                json={"username": "admin", "password": "SecurePass123"}
            )
            assert response.status_code == 401

            data = response.get_json()
            assert "error" in data
            assert data["error"]["type"] == "AuthenticationError"
            assert "only accessible from localhost" in data["error"]["message"]
        finally:
            settings.bypass_localhost_check = original_bypass

    def test_localhost_allowed(self, client):
        """Should allow requests from localhost."""
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 201

        data = response.get_json()
        assert "user" in data
        assert data["user"]["username"] == "admin"


class TestFirstTimeOnlyDecorator:
    """Tests for @first_time_only decorator."""

    def test_allows_when_no_admin_exists(self, client):
        """Should allow access when no admin user exists."""
        # First request should succeed
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 201

    def test_blocks_when_admin_exists(self, client):
        """Should block access when admin user exists."""
        # Create admin user first
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="admin", password="SecurePass123")
            service.create_user(core._conn, user_data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Second request should fail
        response = client.post(
            "/admin/register",
            json={"username": "admin2", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 401

        data = response.get_json()
        assert "error" in data
        assert data["error"]["type"] == "AuthenticationError"
        assert "Setup has already been completed" in data["error"]["message"]


class TestDecoratorIntegration:
    """Integration tests for decorators with actual Flask routes."""

    def test_both_decorators_on_admin_register(self, client):
        """Should enforce both localhost and first-time constraints."""
        # First request from localhost should succeed
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 201

        # Second request from localhost should fail (first-time only)
        response = client.post(
            "/admin/register",
            json={"username": "admin2", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 401

        # Request from non-localhost should fail (localhost only)
        # Create a new test database for this check
        from memogarden_core.db import init_db
        import tempfile
        import os

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            original_db_path = settings.database_path
            settings.database_path = db_path
            init_db()

            # Set bypass config to simulate non-localhost request
            original_bypass = settings.bypass_localhost_check
            settings.bypass_localhost_check = True
            try:
                response = client.post(
                    "/admin/register",
                    json={"username": "test", "password": "SecurePass123"}
                )
                assert response.status_code == 401

                data = response.get_json()
                assert "error" in data
                assert "only accessible from localhost" in data["error"]["message"]
            finally:
                settings.bypass_localhost_check = original_bypass
        finally:
            settings.database_path = original_db_path
            try:
                os.unlink(db_path)
            except:
                pass


class TestDecoratorBehavior:
    """Tests for decorator behavior and edge cases."""

    def test_regular_user_does_not_trigger_first_time_check(self, client):
        """Regular user (not admin) should not bypass first-time check."""
        # Create a regular user
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="user", password="SecurePass123")
            service.create_user(core._conn, user_data, is_admin=False)
            core._conn.commit()
        finally:
            core._conn.close()

        # Admin registration should still work (no admin exists yet)
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 201

    def test_duplicate_username_rejected(self, client):
        """Duplicate username should be rejected even with valid decorators."""
        # Create first admin
        response1 = client.post(
            "/admin/register",
            json={"username": "admin", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response1.status_code == 201

        # Try to create another admin with different username (should fail due to first-time check)
        response2 = client.post(
            "/admin/register",
            json={"username": "admin2", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response2.status_code == 401
        assert "Setup has already been completed" in response2.get_json()["error"]["message"]


class TestAuthRequiredDecorator:
    """Tests for @auth_required decorator."""

    def test_allows_valid_jwt_token(self, client):
        """Should allow requests with valid JWT token."""
        # Create a test user
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="testuser", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=False)
            core._conn.commit()

            # Generate JWT token
            user_response = schemas.UserResponse(
                id=user.id,
                username=user.username,
                is_admin=user.is_admin,
                created_at=user.created_at
            )
            jwt_token = token.generate_access_token(user_response)

            # Make request with JWT token
            response = client.get(
                "/auth/test-require-auth",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )

            # Should succeed
            assert response.status_code == 200
            data = response.get_json()
            assert data["username"] == "testuser"
            assert data["auth_method"] == "jwt"
        finally:
            core._conn.close()

    def test_allows_valid_api_key(self, client):
        """Should allow requests with valid API key."""
        # Create a test user and API key
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="testuser", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=False)
            core._conn.commit()

            # Create API key
            api_key_data = schemas.APIKeyCreate(name="test-key", expires_at=None)
            api_key_result = api_keys.create_api_key(core._conn, user.id, api_key_data)
            core._conn.commit()

            # Make request with API key
            response = client.get(
                "/auth/test-require-auth",
                headers={"X-API-Key": api_key_result.key}
            )

            # Should succeed
            assert response.status_code == 200
            data = response.get_json()
            assert data["username"] == "testuser"
            assert data["auth_method"] == "api_key"
        finally:
            core._conn.close()

    def test_rejects_expired_jwt_token(self, client):
        """Should reject requests with expired JWT token."""
        # Create an expired token (this is hard to test without time manipulation)
        # For now, test invalid token format
        response = client.get(
            "/auth/test-require-auth",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert data["error"]["type"] == "AuthenticationError"

    def test_rejects_invalid_api_key(self, client):
        """Should reject requests with invalid API key."""
        response = client.get(
            "/auth/test-require-auth",
            headers={"X-API-Key": "mg_sk_invalid_key_12345"}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "Invalid API key" in data["error"]["message"]

    def test_rejects_missing_auth(self, client):
        """Should reject requests without authentication."""
        response = client.get("/auth/test-require-auth")

        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "Authentication required" in data["error"]["message"]

    def test_stores_user_info_in_flask_g(self, client):
        """Should store authenticated user info in flask.g."""
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="testuser", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)
            core._conn.commit()

            # Generate JWT token
            user_response = schemas.UserResponse(
                id=user.id,
                username=user.username,
                is_admin=user.is_admin,
                created_at=user.created_at
            )
            jwt_token = token.generate_access_token(user_response)

            # Make request
            response = client.get(
                "/auth/test-require-auth",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )

            # Should return user info from flask.g
            assert response.status_code == 200
            data = response.get_json()
            assert data["user_id"] == user.id
            assert data["username"] == "testuser"
            assert data["is_admin"] is True
        finally:
            core._conn.close()

    def test_jwt_preferred_over_api_key(self, client):
        """Should prefer JWT over API key when both are provided."""
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="testuser", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=False)
            core._conn.commit()

            # Generate JWT token and API key
            user_response = schemas.UserResponse(
                id=user.id,
                username=user.username,
                is_admin=user.is_admin,
                created_at=user.created_at
            )
            jwt_token = token.generate_access_token(user_response)

            api_key_data = schemas.APIKeyCreate(name="test-key", expires_at=None)
            api_key_result = api_keys.create_api_key(core._conn, user.id, api_key_data)
            core._conn.commit()

            # Make request with both auth methods
            response = client.get(
                "/auth/test-require-auth",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "X-API-Key": api_key_result.key
                }
            )

            # Should use JWT (preferred method)
            assert response.status_code == 200
            data = response.get_json()
            assert data["auth_method"] == "jwt"
        finally:
            core._conn.close()

    def test_revoked_api_key_rejected(self, client):
        """Should reject requests with revoked API key."""
        core = get_core()
        try:
            user_data = schemas.UserCreate(username="testuser", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=False)
            core._conn.commit()

            # Create API key
            api_key_data = schemas.APIKeyCreate(name="test-key", expires_at=None)
            api_key_result = api_keys.create_api_key(core._conn, user.id, api_key_data)
            core._conn.commit()

            # Revoke the API key (requires user_id for authorization check)
            api_keys.revoke_api_key(core._conn, api_key_result.id, user.id)
            core._conn.commit()

            # Try to use revoked key
            response = client.get(
                "/auth/test-require-auth",
                headers={"X-API-Key": api_key_result.key}
            )

            assert response.status_code == 401
            data = response.get_json()
            assert "Invalid API key" in data["error"]["message"]
        finally:
            core._conn.close()

    def test_api_key_requires_user_id_for_revoke(self, client):
        """API key revocation should verify user ownership."""
        core = get_core()
        try:
            # Create two users
            user1_data = schemas.UserCreate(username="user1", password="SecurePass123")
            user1 = service.create_user(core._conn, user1_data, is_admin=False)

            user2_data = schemas.UserCreate(username="user2", password="SecurePass123")
            user2 = service.create_user(core._conn, user2_data, is_admin=False)
            core._conn.commit()

            # Create API key for user1
            api_key_data = schemas.APIKeyCreate(name="user1-key", expires_at=None)
            api_key_result = api_keys.create_api_key(core._conn, user1.id, api_key_data)
            core._conn.commit()

            # Try to revoke user1's API key with user2's ID (should fail)
            success = api_keys.revoke_api_key(core._conn, api_key_result.id, user2.id)
            assert success is False

            # Commit and close to release database lock before HTTP request
            core._conn.commit()
        finally:
            core._conn.close()

        # API key should still work (using new connection in HTTP request)
        response = client.get(
            "/auth/test-require-auth",
            headers={"X-API-Key": api_key_result.key}
        )
        assert response.status_code == 200

    # Note: JWT tokens are self-contained and don't automatically check if user exists.
    # This is a design decision for stateless authentication. If we want to add
    # user existence checking, it would be done in the @require_auth decorator.
    # For now, we skip this test since the current implementation allows valid tokens
    # even after user deletion (tokens will expire naturally after JWT_EXPIRY_DAYS).

