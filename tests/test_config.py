"""Tests for configuration management."""

from memogarden.config import Settings


class TestConfiguration:
    """Test configuration loading and defaults."""

    def test_settings_loads(self):
        """Settings should load without errors."""
        settings = Settings()
        assert settings is not None

    def test_default_database_path(self):
        """Default database path should be set."""
        settings = Settings()
        assert settings.database_path == "./data/memogarden.db"

    def test_default_api_prefix(self):
        """Default API prefix should be set."""
        settings = Settings()
        assert settings.api_v1_prefix == "/api/v1"

    def test_default_currency(self):
        """Default currency should be SGD."""
        settings = Settings()
        assert settings.default_currency == "SGD"

    def test_cors_origins_is_list(self):
        """CORS origins should be a list."""
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert "http://localhost:3000" in settings.cors_origins
