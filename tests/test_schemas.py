"""
Tests for Pydantic schemas (API validation).

Tests verify that:
- Transaction schemas validate data correctly
- Field types and constraints are enforced
- Optional fields work as expected
- Serialization/deserialization works properly
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from memogarden_core.api.v1.schemas import (
    TransactionBase,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
)


class TestTransactionCreate:
    """Tests for TransactionCreate schema."""

    def test_create_with_all_fields(self):
        """Test creating transaction with all fields."""
        data = {
            "amount": -15.50,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Coffee at Starbucks",
            "account": "Personal",
            "category": "Food",
            "notes": "Morning coffee",
        }
        transaction = TransactionCreate(**data)

        assert transaction.amount == -15.50
        assert transaction.currency == "SGD"
        assert transaction.transaction_date == date(2025, 12, 23)
        assert transaction.description == "Coffee at Starbucks"
        assert transaction.account == "Personal"
        assert transaction.category == "Food"
        assert transaction.notes == "Morning coffee"

    def test_create_with_minimal_fields(self):
        """Test creating transaction with only required fields."""
        data = {
            "amount": 100.00,
            "transaction_date": "2025-12-23",
            "account": "Household",
        }
        transaction = TransactionCreate(**data)

        assert transaction.amount == 100.00
        assert transaction.currency == "SGD"  # Default value
        assert transaction.transaction_date == date(2025, 12, 23)
        assert transaction.description == ""  # Default value
        assert transaction.account == "Household"
        assert transaction.category is None  # Optional field
        assert transaction.notes is None  # Optional field

    def test_create_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        data = {
            "amount": 50.00,
            # Missing transaction_date and account
        }
        with pytest.raises(ValidationError) as exc_info:
            TransactionCreate(**data)

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}
        assert "transaction_date" in error_fields
        assert "account" in error_fields

    def test_create_invalid_date_format(self):
        """Test that invalid date format raises validation error."""
        data = {
            "amount": 50.00,
            "transaction_date": "23-12-2025",  # Wrong format
            "account": "Personal",
        }
        with pytest.raises(ValidationError):
            TransactionCreate(**data)

    def test_create_with_custom_currency(self):
        """Test creating transaction with non-default currency."""
        data = {
            "amount": 20.00,
            "currency": "USD",
            "transaction_date": "2025-12-23",
            "account": "Personal",
        }
        transaction = TransactionCreate(**data)
        assert transaction.currency == "USD"

    def test_create_account_is_label_not_fk(self):
        """Test that account is a string label, not a foreign key."""
        # Account can be any string - no validation against a table
        data = {
            "amount": 10.00,
            "transaction_date": "2025-12-23",
            "account": "New Account That Doesn't Exist Yet",
        }
        transaction = TransactionCreate(**data)
        assert transaction.account == "New Account That Doesn't Exist Yet"

    def test_create_category_is_label_not_fk(self):
        """Test that category is a string label, not a foreign key."""
        # Category can be any string - no validation against a table
        data = {
            "amount": 10.00,
            "transaction_date": "2025-12-23",
            "account": "Personal",
            "category": "Custom Category 123",
        }
        transaction = TransactionCreate(**data)
        assert transaction.category == "Custom Category 123"


class TestTransactionUpdate:
    """Tests for TransactionUpdate schema."""

    def test_update_all_fields_optional(self):
        """Test that all fields are optional in update schema."""
        # Empty update should be valid
        transaction = TransactionUpdate()
        assert transaction.amount is None
        assert transaction.currency is None
        assert transaction.transaction_date is None
        assert transaction.description is None
        assert transaction.account is None
        assert transaction.category is None
        assert transaction.notes is None

    def test_update_single_field(self):
        """Test updating only one field."""
        data = {"amount": -20.00}
        transaction = TransactionUpdate(**data)

        assert transaction.amount == -20.00
        assert transaction.currency is None
        assert transaction.account is None

    def test_update_multiple_fields(self):
        """Test updating multiple fields."""
        data = {
            "amount": -30.00,
            "category": "Food & Drinks",
            "notes": "Updated notes",
        }
        transaction = TransactionUpdate(**data)

        assert transaction.amount == -30.00
        assert transaction.category == "Food & Drinks"
        assert transaction.notes == "Updated notes"
        assert transaction.account is None  # Not updated

    def test_update_clear_optional_field(self):
        """Test clearing an optional field by setting to None."""
        data = {"category": None}
        transaction = TransactionUpdate(**data)
        assert transaction.category is None


class TestTransactionResponse:
    """Tests for TransactionResponse schema."""

    def test_response_with_full_data(self):
        """Test response schema with all fields."""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "amount": -15.50,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Coffee at Starbucks",
            "account": "Personal",
            "category": "Food",
            "notes": "Morning coffee",
            "author": "user@example.com",
            "recurrence_id": None,
            "created_at": "2025-12-23T06:31:33.544668Z",
            "updated_at": "2025-12-23T06:31:33.544668Z",
            "superseded_by": None,
            "superseded_at": None,
            "group_id": None,
            "derived_from": None,
        }
        transaction = TransactionResponse(**data)

        assert transaction.id == "550e8400-e29b-41d4-a716-446655440000"
        assert transaction.amount == -15.50
        assert transaction.author == "user@example.com"
        assert transaction.created_at == datetime.fromisoformat("2025-12-23T06:31:33.544668+00:00")

    def test_response_includes_entity_metadata(self):
        """Test that response includes all entity metadata fields."""
        data = {
            "id": "test-id-123",
            "amount": 100.00,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Test",
            "account": "Test Account",
            "author": "system",
            "created_at": "2025-12-23T00:00:00Z",
            "updated_at": "2025-12-23T00:00:00Z",
        }
        transaction = TransactionResponse(**data)

        # Entity metadata fields exist
        assert hasattr(transaction, "created_at")
        assert hasattr(transaction, "updated_at")
        assert hasattr(transaction, "superseded_by")
        assert hasattr(transaction, "superseded_at")
        assert hasattr(transaction, "group_id")
        assert hasattr(transaction, "derived_from")

    def test_response_with_supersession(self):
        """Test response when transaction is superseded."""
        data = {
            "id": "old-id",
            "amount": 100.00,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Old transaction",
            "account": "Personal",
            "author": "system",
            "created_at": "2025-12-23T00:00:00Z",
            "updated_at": "2025-12-23T00:00:00Z",
            "superseded_by": "new-id",
            "superseded_at": "2025-12-23T12:00:00Z",
            "group_id": None,
            "derived_from": None,
        }
        transaction = TransactionResponse(**data)

        assert transaction.superseded_by == "new-id"
        assert transaction.superseded_at == datetime.fromisoformat("2025-12-23T12:00:00+00:00")

    def test_response_with_recurrence(self):
        """Test response when transaction is part of a recurrence."""
        data = {
            "id": "transaction-id",
            "amount": 50.00,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Recurring bill",
            "account": "Household",
            "author": "system",
            "recurrence_id": "recurrence-template-id",
            "created_at": "2025-12-23T00:00:00Z",
            "updated_at": "2025-12-23T00:00:00Z",
        }
        transaction = TransactionResponse(**data)
        assert transaction.recurrence_id == "recurrence-template-id"

    def test_response_default_author(self):
        """Test that author defaults to 'system' if not provided."""
        data = {
            "id": "test-id",
            "amount": 100.00,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Test",
            "account": "Personal",
            "created_at": "2025-12-23T00:00:00Z",
            "updated_at": "2025-12-23T00:00:00Z",
        }
        transaction = TransactionResponse(**data)
        assert transaction.author == "system"

    def test_response_serialization(self):
        """Test that response can be serialized to JSON."""
        data = {
            "id": "test-id",
            "amount": 100.00,
            "currency": "SGD",
            "transaction_date": "2025-12-23",
            "description": "Test",
            "account": "Personal",
            "author": "user@example.com",
            "created_at": "2025-12-23T00:00:00Z",
            "updated_at": "2025-12-23T00:00:00Z",
        }
        transaction = TransactionResponse(**data)

        # Test that it can be serialized
        json_dict = transaction.model_dump()
        assert json_dict["id"] == "test-id"
        assert json_dict["amount"] == 100.00

        # Test JSON mode
        json_str = transaction.model_dump_json()
        assert "test-id" in json_str
        assert "100.0" in json_str or "100" in json_str


class TestTransactionBase:
    """Tests for TransactionBase schema (shared fields)."""

    def test_base_shared_fields(self):
        """Test that base schema has all expected shared fields."""
        data = {
            "amount": 50.00,
            "currency": "USD",
            "transaction_date": "2025-12-23",
            "description": "Test transaction",
            "account": "Personal",
            "category": "Food",
            "notes": "Some notes",
        }
        transaction = TransactionBase(**data)

        assert transaction.amount == 50.00
        assert transaction.currency == "USD"
        assert transaction.transaction_date == date(2025, 12, 23)
        assert transaction.description == "Test transaction"
        assert transaction.account == "Personal"
        assert transaction.category == "Food"
        assert transaction.notes == "Some notes"
