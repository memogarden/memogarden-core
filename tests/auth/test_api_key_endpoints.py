"""Tests for API key management endpoints.

Tests API key list, create, and revoke endpoints.
"""

import json
import pytest
from flask import Flask
from datetime import datetime

from memogarden.db import get_core
from memogarden.auth import service
from memogarden.auth.schemas import UserCreate, APIKeyCreate
from memogarden.auth.token import generate_access_token


# ============================================================================
# API Key List Endpoint Tests
# ============================================================================


class TestListAPIKeys:
    """Tests for GET /api-keys/ endpoint."""

    def test_list_api_keys_with_valid_token(self, client: Flask.test_client):
        """GET /api-keys/ should return list of API keys for authenticated user."""
        # Create user and get token
        core = get_core()
        try:
            user_data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)
            core._conn.commit()

            token = generate_access_token(user)
        finally:
            core._conn.close()

        # List API keys
        response = client.get(
            "/api-keys/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        # Initially empty list
        assert len(data) == 0

    def test_list_api_keys_without_token(self, client: Flask.test_client):
        """GET /api-keys/ should fail without token."""
        response = client.get("/api-keys/")
        assert response.status_code == 401

    def test_list_api_keys_with_multiple_keys(self, client: Flask.test_client):
        """GET /api-keys/ should return all API keys (without full keys)."""
        # Create user and get token
        core = get_core()
        try:
            user_data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)

            # Create multiple API keys
            from memogarden.auth import api_keys
            data1 = APIKeyCreate(name="key1", expires_at=None)
            data2 = APIKeyCreate(name="key2", expires_at=None)
            api_keys.create_api_key(core._conn, user.id, data1)
            api_keys.create_api_key(core._conn, user.id, data2)
            core._conn.commit()

            token = generate_access_token(user)
        finally:
            core._conn.close()

        # List API keys
        response = client.get(
            "/api-keys/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2

        # Verify full keys are not included
        for api_key in data:
            assert "key" not in api_key  # No full key in list
            assert api_key["prefix"] == "mg_sk_agent_"


# ============================================================================
# API Key Create Endpoint Tests
# ============================================================================


class TestCreateAPIKey:
    """Tests for POST /api-keys/ endpoint."""

    def test_create_api_key_success(self, client: Flask.test_client):
        """POST /api-keys/ should create API key and return full key."""
        # Create user and get token
        core = get_core()
        try:
            user_data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)
            core._conn.commit()

            token = generate_access_token(user)
        finally:
            core._conn.close()

        # Create API key
        response = client.post(
            "/api-keys/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "test-key", "expires_at": None}
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert "id" in data
        assert data["name"] == "test-key"
        assert "key" in data  # Full key shown on creation
        assert data["prefix"] == "mg_sk_agent_"
        assert data["expires_at"] is None
        assert data["revoked_at"] is None

    def test_create_api_key_with_expiration(self, client: Flask.test_client):
        """POST /api-keys/ should create API key with expiration."""
        # Create user and get token
        core = get_core()
        try:
            user_data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)
            core._conn.commit()

            token = generate_access_token(user)
        finally:
            core._conn.close()

        # Create API key with expiration
        expires_at = "2026-12-31T23:59:59Z"
        response = client.post(
            "/api-keys/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "test-key", "expires_at": expires_at}
        )
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["expires_at"] is not None  # Just check it's present

    def test_create_api_key_without_token(self, client: Flask.test_client):
        """POST /api-keys/ should fail without token."""
        response = client.post(
            "/api-keys/",
            json={"name": "test-key", "expires_at": None}
        )
        assert response.status_code == 401


# ============================================================================
# API Key Revoke Endpoint Tests
# ============================================================================


class TestRevokeAPIKey:
    """Tests for DELETE /api-keys/:id endpoint."""

    def test_revoke_api_key_success(self, client: Flask.test_client):
        """DELETE /api-keys/:id should revoke API key."""
        # Create user and API key
        core = get_core()
        try:
            user_data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)

            from memogarden.auth import api_keys
            data = APIKeyCreate(name="test-key", expires_at=None)
            api_key = api_keys.create_api_key(core._conn, user.id, data)
            core._conn.commit()

            token = generate_access_token(user)
        finally:
            core._conn.close()

        # Revoke API key
        response = client.delete(
            f"/api-keys/{api_key.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["message"] == "API key revoked successfully"

    def test_revoke_api_key_without_token(self, client: Flask.test_client):
        """DELETE /api-keys/:id should fail without token."""
        response = client.delete("/api-keys/some-id")
        assert response.status_code == 401

    def test_revoke_api_key_not_found(self, client: Flask.test_client):
        """DELETE /api-keys/:id should return 404 for non-existent key."""
        # Create user and get token
        core = get_core()
        try:
            user_data = UserCreate(username="admin", password="SecurePass123")
            user = service.create_user(core._conn, user_data, is_admin=True)
            core._conn.commit()

            token = generate_access_token(user)
        finally:
            core._conn.close()

        # Try to revoke non-existent key
        response = client.delete(
            "/api-keys/550e8400-e29b-41d4-a716-446655440000",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
