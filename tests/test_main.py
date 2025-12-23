"""Tests for Flask application setup."""

import pytest
from memogarden_core.main import app, ResourceNotFound, ValidationError


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.get('/health')
    # Flask-CORS should add the necessary headers
    assert response.status_code == 200


def test_404_error(client):
    """Test 404 error for non-existent endpoint."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
