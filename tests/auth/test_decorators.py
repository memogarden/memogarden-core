"""Tests for authentication decorators.

Tests the @localhost_only and @first_time_only decorators that enforce
security constraints on protected endpoints.
"""

import pytest
from memogarden_core.auth import decorators, schemas, service
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
