"""Tests for authentication endpoints.

Tests admin registration, login, logout, and user profile endpoints.
"""

import json
import pytest
from flask import Flask
from memogarden_core.db import get_core
from memogarden_core.auth import service
from memogarden_core.auth.schemas import UserCreate
from memogarden_core.auth.token import generate_access_token
from memogarden_core.config import settings


# ============================================================================
# Admin Registration Endpoints
# ============================================================================


class TestAdminRegisterPage:
    """Tests for GET /admin/register endpoint."""

    def test_admin_register_page_no_users(self, client: Flask.test_client):
        """GET /admin/register should return HTML when no users exist."""
        response = client.get("/admin/register", base_url="http://localhost:5000")
        assert response.status_code == 200
        assert b"<title>MemoGarden - Admin Setup</title>" in response.data
        assert b"<form" in response.data

    def test_admin_register_page_from_non_localhost(self, client: Flask.test_client):
        """GET /admin/register should return 403 from non-localhost."""
        # Set bypass config to simulate non-localhost request
        original_bypass = settings.bypass_localhost_check
        settings.bypass_localhost_check = True
        try:
            response = client.get("/admin/register")
            assert response.status_code == 403

            data = json.loads(response.data)
            assert "error" in data
            assert data["error"]["type"] == "Forbidden"
            assert "localhost" in data["error"]["message"].lower()
        finally:
            settings.bypass_localhost_check = original_bypass

    def test_admin_register_page_admin_exists(self, client: Flask.test_client):
        """GET /admin/register should return HTML with error when admin exists."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Try to access registration page
        response = client.get("/admin/register", base_url="http://localhost:5000")
        assert response.status_code == 200
        assert b"Admin account already exists" in response.data


class TestAdminRegister:
    """Tests for POST /admin/register endpoint."""

    def test_admin_register_success(self, client: Flask.test_client):
        """POST /admin/register should create admin account."""
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "SecurePass123"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "message" in data
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["is_admin"] is True
        assert "password" not in data["user"]  # Password should not be in response

    def test_admin_register_from_non_localhost(self, client: Flask.test_client):
        """POST /admin/register should return 401 from non-localhost."""
        # Set bypass config to simulate non-localhost request
        original_bypass = settings.bypass_localhost_check
        settings.bypass_localhost_check = True
        try:
            response = client.post(
                "/admin/register",
                json={"username": "admin", "password": "SecurePass123"}
            )
            assert response.status_code == 401

            data = json.loads(response.data)
            assert "error" in data
            assert data["error"]["type"] == "AuthenticationError"
        finally:
            settings.bypass_localhost_check = original_bypass

    def test_admin_register_duplicate_username(self, client: Flask.test_client):
        """POST /admin/register should fail with duplicate username."""
        # Create admin first
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Try to create again
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "DifferentPass456"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data

    def test_admin_register_weak_password(self, client: Flask.test_client):
        """POST /admin/register should fail with weak password."""
        response = client.post(
            "/admin/register",
            json={"username": "admin", "password": "weak"},
            base_url="http://localhost:5000"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data
        assert data["error"]["type"] == "ValidationError"

    def test_admin_register_missing_fields(self, client: Flask.test_client):
        """POST /admin/register should fail with missing fields."""
        response = client.post(
            "/admin/register",
            json={"username": "admin"},  # Missing password
            base_url="http://localhost:5000"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data


# ============================================================================
# Login Endpoint
# ============================================================================


class TestLogin:
    """Tests for POST /auth/login endpoint."""

    def test_login_success(self, client: Flask.test_client):
        """POST /auth/login should return JWT token for valid credentials."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Login
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "SecurePass123"}
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["is_admin"] is True

    def test_login_invalid_password(self, client: Flask.test_client):
        """POST /auth/login should fail with invalid password."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Login with wrong password
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "WrongPassword"}
        )
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data
        assert data["error"]["type"] == "AuthenticationError"

    def test_login_invalid_username(self, client: Flask.test_client):
        """POST /auth/login should fail with invalid username."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "SecurePass123"}
        )
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data

    def test_login_missing_fields(self, client: Flask.test_client):
        """POST /auth/login should fail with missing fields."""
        response = client.post(
            "/auth/login",
            json={"username": "admin"}  # Missing password
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_login_case_insensitive_username(self, client: Flask.test_client):
        """POST /auth/login should be case-insensitive for username."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Login with uppercase username
        response = client.post(
            "/auth/login",
            json={"username": "ADMIN", "password": "SecurePass123"}
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "access_token" in data

    def test_login_password_case_sensitive(self, client: Flask.test_client):
        """POST /auth/login should be case-sensitive for password."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Login with lowercase password
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "securepass123"}
        )
        assert response.status_code == 401


# ============================================================================
# Logout Endpoint
# ============================================================================


class TestLogout:
    """Tests for POST /auth/logout endpoint."""

    def test_logout_success(self, client: Flask.test_client):
        """POST /auth/logout should return success message."""
        response = client.post("/auth/logout")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["message"] == "Logged out successfully"


# ============================================================================
# User Profile Endpoint
# ============================================================================


class TestGetCurrentUser:
    """Tests for GET /auth/me endpoint."""

    def test_get_current_user_with_valid_token(self, client: Flask.test_client):
        """GET /auth/me should return user info for valid token."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Generate token
        token = generate_access_token(user)

        # Get current user
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["id"] == user.id
        assert data["username"] == "admin"
        assert data["is_admin"] is True
        assert "password" not in data

    def test_get_current_user_missing_token(self, client: Flask.test_client):
        """GET /auth/me should fail without token."""
        response = client.get("/auth/me")
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data

    def test_get_current_user_invalid_token(self, client: Flask.test_client):
        """GET /auth/me should fail with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data

    def test_get_current_user_malformed_header(self, client: Flask.test_client):
        """GET /auth/me should fail with malformed Authorization header."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data

    def test_get_current_user_deleted_user(self, client: Flask.test_client):
        """GET /auth/me should fail if user was deleted."""
        # Create admin user
        core = get_core()
        try:
            data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, data, is_admin=True)
            core._conn.commit()
        finally:
            core._conn.close()

        # Generate token
        token = generate_access_token(user)

        # Delete user
        core = get_core()
        try:
            core._conn.execute("DELETE FROM users WHERE id = ?", (user.id,))
            core._conn.commit()
        finally:
            core._conn.close()

        # Try to get current user
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

        data = json.loads(response.data)
        assert "error" in data
