"""Tests for the @validate_request decorator."""

import pytest
from datetime import date
from pydantic import BaseModel, Field

from memogarden.main import app
from memogarden.api.validation import validate_request
from memogarden.exceptions import ValidationError as MGValidationError


# Test Pydantic schemas
class MockCreateRequest(BaseModel):
    """Test schema for request body validation."""
    name: str = Field(..., description="Name field")
    amount: float = Field(..., description="Amount field")
    category: str | None = Field(default=None, description="Optional category")


class MockUpdateRequest(BaseModel):
    """Test schema with all optional fields."""
    name: str | None = None
    amount: float | None = None


# Register test routes globally (before any requests)
from flask import Blueprint, jsonify

test_validation_bp = Blueprint('validation_test_routes', __name__)

# Route: Valid request body
@test_validation_bp.post("/test/valid")
@validate_request
def route_valid(data: MockCreateRequest):
    return jsonify({
        "name": data.name,
        "amount": data.amount,
        "category": data.category
    }), 200

# Route: Invalid request body (missing required field)
@test_validation_bp.post("/test/invalid")
@validate_request
def route_invalid(data: MockCreateRequest):
    return jsonify({"status": "ok"}), 200

# Route: Path parameter only
@test_validation_bp.get("/test/path/<uuid>")
@validate_request
def route_path_param(uuid: str):
    return jsonify({"uuid": uuid}), 200

# Route: Path parameter + body
@test_validation_bp.put("/test/combined/<uuid>")
@validate_request
def route_combined(uuid: str, data: MockUpdateRequest):
    return jsonify({
        "uuid": uuid,
        "name": data.name,
        "amount": data.amount
    }), 200

# Route: Missing body
@test_validation_bp.post("/test/missing-body")
@validate_request
def route_missing_body(data: MockCreateRequest):
    return jsonify({"status": "ok"}), 200

# Register blueprint on app module import
app.register_blueprint(test_validation_bp)


# Fixtures
@pytest.fixture
def validation_client():
    """Create test client with validation test routes."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# Tests
def test_validates_valid_request_body(validation_client):
    """Valid request body should pass validation and be parsed correctly."""
    response = validation_client.post(
        "/test/valid",
        json={
            "name": "Test Transaction",
            "amount": 100.50,
            "category": "Food"
        },
        content_type="application/json"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Test Transaction"
    assert data["amount"] == 100.50
    assert data["category"] == "Food"


def test_validates_with_optional_field_omitted(validation_client):
    """Request with optional field omitted should still pass validation."""
    response = validation_client.post(
        "/test/valid",
        json={
            "name": "Test",
            "amount": 50.0
        },
        content_type="application/json"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Test"
    assert data["amount"] == 50.0
    assert data["category"] is None


def test_raises_mgvalidationerror_for_missing_required_field(validation_client):
    """Missing required field should raise MGValidationError with details."""
    response = validation_client.post(
        "/test/invalid",
        json={
            "name": "Test"
            # Missing required 'amount' field
        },
        content_type="application/json"
    )

    assert response.status_code == 400
    data = response.get_json()

    # Check error structure
    assert "error" in data
    assert data["error"]["type"] == "ValidationError"
    error_details = data["error"]["details"]

    # Should include error details
    assert "errors" in error_details
    errors = error_details["errors"]

    # Check that amount field error is present
    amount_errors = [e for e in errors if "amount" in e.get("field", "")]
    assert len(amount_errors) > 0


def test_error_details_include_field_and_message(validation_client):
    """Validation errors should include field, message, and expected_type."""
    response = validation_client.post(
        "/test/invalid",
        json={
            "amount": "not_a_number"  # Wrong type
        },
        content_type="application/json"
    )

    assert response.status_code == 400
    data = response.get_json()
    error_details = data["error"]["details"]

    assert "errors" in error_details
    errors = error_details["errors"]

    # Each error should have field, message, and expected_type
    for error in errors:
        assert "field" in error
        assert "message" in error
        assert "expected_type" in error


def test_raises_clear_error_when_body_is_empty_json(validation_client):
    """Empty JSON body should return clear validation error for missing required fields."""
    # Send empty JSON object
    response = validation_client.post(
        "/test/missing-body",
        json={}
    )

    assert response.status_code == 400
    data = response.get_json()
    error_details = data["error"]["details"]

    # Should indicate validation failure
    assert "model" in error_details
    assert error_details["model"] == "MockCreateRequest"
    assert "received" in error_details
    assert error_details["received"] == {}
    assert "errors" in error_details

    # Should have errors for required fields
    errors = error_details["errors"]
    field_names = [e["field"] for e in errors]
    assert "name" in field_names
    assert "amount" in field_names


def test_passes_through_path_parameters_unchanged(validation_client):
    """Path parameters should be passed as strings, not validated."""
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"

    response = validation_client.get(f"/test/path/{test_uuid}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["uuid"] == test_uuid


def test_path_param_with_body(validation_client):
    """Routes with both path param and body should handle both correctly."""
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"

    response = validation_client.put(
        f"/test/combined/{test_uuid}",
        json={
            "name": "Updated Name",
            "amount": 200.0
        },
        content_type="application/json"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["uuid"] == test_uuid
    assert data["name"] == "Updated Name"
    assert data["amount"] == 200.0


def test_raises_typeerror_when_function_has_no_parameters():
    """Decorator should raise TypeError when function has no parameters."""
    def no_params():
        return "ok"

    with pytest.raises(TypeError) as exc_info:
        validate_request(no_params)

    assert "has no parameters to validate" in str(exc_info.value)


def test_raises_typeerror_when_first_param_lacks_annotation():
    """Decorator should raise TypeError when first param lacks type annotation."""
    def no_annotation(data):
        return "ok"

    with pytest.raises(TypeError) as exc_info:
        validate_request(no_annotation)

    assert "lacks a type annotation" in str(exc_info.value)


def test_raises_typeerror_for_body_param_without_basemodel():
    """Body parameters without BaseModel annotation should raise TypeError at request time."""
    # This test verifies that non-BaseModel annotations raise errors
    # when the decorator is used for a function that will receive body data

    # Create a mock Flask request context where the param is NOT in view_args
    def wrong_annotation(data: str):
        return "ok"

    decorated = validate_request(wrong_annotation)

    # When used in a request context without the param in view_args,
    # it should check for BaseModel and raise TypeError
    with app.test_request_context('/test', method='POST', json='{"data": "test"}'):
        # Set up view_args without the parameter
        from flask import request
        request.view_args = {}

        with pytest.raises(TypeError) as exc_info:
            decorated()

        assert "Pydantic BaseModel subclass" in str(exc_info.value)


def test_validation_error_includes_received_data(validation_client):
    """Validation error should include the received data for debugging."""
    response = validation_client.post(
        "/test/invalid",
        json={
            "name": "Test",
            "amount": "wrong_type",  # Should be float
            "extra_field": "not_in_schema"
        },
        content_type="application/json"
    )

    assert response.status_code == 400
    data = response.get_json()
    error_details = data["error"]["details"]

    # Should include received data
    assert "received" in error_details
    assert error_details["received"]["name"] == "Test"
    assert error_details["received"]["amount"] == "wrong_type"


def test_wrong_type_returns_clear_error(validation_client):
    """Wrong type for a field should return clear error message."""
    response = validation_client.post(
        "/test/invalid",
        json={
            "name": "Test",
            "amount": "not_a_number"  # Should be float
        },
        content_type="application/json"
    )

    assert response.status_code == 400
    data = response.get_json()
    error_details = data["error"]["details"]

    # Should have errors
    assert "errors" in error_details
    errors = error_details["errors"]

    # Find amount error
    amount_errors = [e for e in errors if "amount" in e.get("field", "")]
    assert len(amount_errors) > 0

    # Error should indicate type issue
    amount_error = amount_errors[0]
    assert "float" in amount_error.get("expected_type", "").lower() or "number" in amount_error.get("message", "").lower()
