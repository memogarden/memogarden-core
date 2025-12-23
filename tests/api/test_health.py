"""Tests for API health endpoint."""

import pytest


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 status."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health endpoint should return JSON."""
        response = client.get("/health")

        # Should be valid JSON
        data = response.get_json()
        assert isinstance(data, dict)

    def test_health_returns_status_ok(self, client):
        """Health endpoint should return status ok."""
        response = client.get("/health")
        data = response.get_json()

        assert data["status"] == "ok"
