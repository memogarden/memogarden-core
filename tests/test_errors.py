"""Tests for error handling and custom exceptions."""

import pytest
from flask import Flask
from memogarden.main import app
from memogarden.exceptions import (
    ResourceNotFound,
    ValidationError,
    DatabaseError,
    MemoGardenError
)


@pytest.fixture
def error_app():
    """Create a test app with error testing routes."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    # Disable trap so exceptions propagate to error handlers
    test_app.config['TRAP_HTTP_EXCEPTIONS'] = True
    test_app.config['TRAP_BAD_REQUEST_ERRORS'] = True

    # Copy error handlers from main app
    from memogarden.main import handle_not_found, handle_validation_error
    from memogarden.main import handle_memo_garden_error, handle_internal_error

    test_app.errorhandler(ResourceNotFound)(handle_not_found)
    test_app.errorhandler(ValidationError)(handle_validation_error)
    test_app.errorhandler(MemoGardenError)(handle_memo_garden_error)
    test_app.errorhandler(Exception)(handle_internal_error)

    # Register test routes
    @test_app.route('/test/not-found')
    def test_not_found():
        raise ResourceNotFound("Transaction not found", details={"id": "123"})

    @test_app.route('/test/not-found-no-details')
    def test_not_found_no_details():
        raise ResourceNotFound("Not found")

    @test_app.route('/test/validation')
    def test_validation():
        raise ValidationError("Invalid amount", details={"field": "amount"})

    @test_app.route('/test/database')
    def test_database():
        raise DatabaseError("Connection failed")

    @test_app.route('/test/internal')
    def test_internal():
        raise RuntimeError("Something went wrong")

    return test_app


@pytest.fixture
def error_client(error_app):
    """Create test client for error testing."""
    return error_app.test_client()


class TestExceptionClasses:
    """Test custom exception classes."""

    def test_base_error_exists(self):
        """MemoGardenError base class should exist."""
        assert MemoGardenError is not None

    def test_base_error_with_message(self):
        """Base exception should accept message."""
        error = MemoGardenError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"

    def test_base_error_with_details(self):
        """Base exception should accept details dict."""
        details = {"transaction_id": "123", "reason": "not found"}
        error = MemoGardenError("Not found", details=details)
        assert error.details == details

    def test_base_error_without_details(self):
        """Base exception should have empty details dict by default."""
        error = MemoGardenError("Test")
        assert error.details == {}

    def test_resource_not_found_inherits_base(self):
        """ResourceNotFound should inherit from MemoGardenError."""
        assert issubclass(ResourceNotFound, MemoGardenError)

    def test_validation_error_inherits_base(self):
        """ValidationError should inherit from MemoGardenError."""
        assert issubclass(ValidationError, MemoGardenError)

    def test_database_error_inherits_base(self):
        """DatabaseError should inherit from MemoGardenError."""
        assert issubclass(DatabaseError, MemoGardenError)

    def test_resource_not_found_message(self):
        """ResourceNotFound should store message."""
        error = ResourceNotFound("Transaction not found")
        assert error.message == "Transaction not found"

    def test_validation_error_with_details(self):
        """ValidationError should support details."""
        error = ValidationError("Invalid amount", details={"field": "amount", "value": -10})
        assert error.message == "Invalid amount"
        assert error.details == {"field": "amount", "value": -10}


class TestErrorHandlers:
    """Test Flask error handlers."""

    def test_not_found_error_response_format(self, error_client):
        """ResourceNotFound error should return correct JSON format."""
        response = error_client.get('/test/not-found')
        data = response.get_json()

        assert response.status_code == 404
        assert "error" in data
        assert data["error"]["type"] == "ResourceNotFound"
        assert data["error"]["message"] == "Transaction not found"
        assert data["error"]["details"] == {"id": "123"}

    def test_validation_error_response_format(self, error_client):
        """ValidationError error should return correct JSON format."""
        response = error_client.get('/test/validation')
        data = response.get_json()

        assert response.status_code == 400
        assert "error" in data
        assert data["error"]["type"] == "ValidationError"
        assert data["error"]["message"] == "Invalid amount"
        assert data["error"]["details"] == {"field": "amount"}

    def test_database_error_response_format(self, error_client):
        """DatabaseError error should return 500 status."""
        response = error_client.get('/test/database')
        data = response.get_json()

        assert response.status_code == 500
        assert "error" in data
        assert data["error"]["type"] == "DatabaseError"

    def test_error_without_details(self, error_client):
        """Error without details should not include details key."""
        response = error_client.get('/test/not-found-no-details')
        data = response.get_json()

        assert response.status_code == 404
        assert "error" in data
        assert "details" not in data["error"]

    def test_internal_server_error_handler(self, error_client):
        """Generic 500 errors should return internal error format."""
        response = error_client.get('/test/internal')
        data = response.get_json()

        assert response.status_code == 500
        assert "error" in data
        assert data["error"]["type"] == "InternalServerError"
        assert data["error"]["message"] == "An internal error occurred"
