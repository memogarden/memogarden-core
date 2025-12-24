"""Tests for Flask application initialization and configuration."""

import pytest
from memogarden_core.main import app
from memogarden_core.config import settings


class TestAppInitialization:
    """Test Flask application initialization."""

    def test_app_exists(self):
        """Flask app should be created."""
        assert app is not None

    def test_app_is_flask_instance(self):
        """App should be a Flask application."""
        from flask import Flask
        assert isinstance(app, Flask)

    def test_app_has_name(self):
        """App should have a name."""
        assert app.name is not None

    def test_app_in_testing_mode_when_configured(self, client):
        """App should respect TESTING configuration."""
        assert app.config['TESTING'] is True


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_headers_present_on_health(self, client):
        """CORS headers should be present on API responses."""
        response = client.get("/health")

        # Flask-CORS should add CORS headers
        assert "Access-Control-Allow-Origin" in response.headers

    def test_cors_preflight_options_request(self, client):
        """OPTIONS preflight request should be handled."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should return 200 or 204 for preflight
        assert response.status_code in (200, 204)


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_logger_exists(self):
        """App logger should exist."""
        import logging
        logger = logging.getLogger("memogarden_core.main")
        assert logger is not None

    def test_logging_level_configured(self):
        """Logging should be configured (root logger should have handlers)."""
        import logging
        # Root logger should have at least one handler after app import
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0


class TestHealthEndpoint:
    """Test health check endpoint (app-level tests)."""

    def test_health_route_registered(self):
        """Health route should be registered."""
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/health" in rules

    def test_health_returns_200(self, client):
        """Health endpoint should return 200 status."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health endpoint should return JSON."""
        response = client.get("/health")
        data = response.get_json()
        assert isinstance(data, dict)

    def test_health_returns_status_ok(self, client):
        """Health endpoint should return status ok."""
        response = client.get("/health")
        data = response.get_json()
        assert data["status"] == "ok"
