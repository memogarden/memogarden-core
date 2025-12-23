"""Comprehensive API tests for transaction CRUD endpoints."""

import pytest
import sqlite3
from datetime import date, datetime, UTC
from uuid import uuid4

from memogarden_core.main import app
from memogarden_core.database import create_entity


@pytest.fixture(autouse=True)
def setup_database(client):
    """Set up test database with sample data for each test."""
    with app.app_context():
        from memogarden_core.database import get_db
        db = get_db()

        # Create some test transactions
        # Transaction 1
        entity_id_1 = str(uuid4())
        create_entity(db, "transactions", entity_id_1)
        db.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_1, -15.50, "SGD", "2025-12-23", "Coffee at Starbucks",
             "Personal", "Food", "system", "Morning coffee")
        )

        # Transaction 2
        entity_id_2 = str(uuid4())
        create_entity(db, "transactions", entity_id_2)
        db.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_2, -50.00, "SGD", "2025-12-22", "Grocery shopping",
             "Household", "Food", "system", "Weekly groceries")
        )

        # Transaction 3
        entity_id_3 = str(uuid4())
        create_entity(db, "transactions", entity_id_3)
        db.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_3, -25.00, "SGD", "2025-12-21", "Taxi to airport",
             "Personal", "Transport", "system", "Airport ride")
        )

        # Transaction 4 (no category)
        entity_id_4 = str(uuid4())
        create_entity(db, "transactions", entity_id_4)
        db.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_4, 1000.00, "SGD", "2025-12-20", "Salary deposit",
             "Household", None, "system", "Monthly salary")
        )

        # Transaction 5 (older date, for filtering tests)
        entity_id_5 = str(uuid4())
        create_entity(db, "transactions", entity_id_5)
        db.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_5, -8.00, "SGD", "2025-11-15", "Bus fare",
             "Personal", "Transport", "system", "Monthly pass")
        )

        db.commit()

    yield

    # Cleanup
    with app.app_context():
        from memogarden_core.database import get_db
        db = get_db()
        db.execute("DELETE FROM transactions")
        db.execute("DELETE FROM entity")
        db.commit()


class TestCreateTransaction:
    """Tests for POST /api/v1/transactions"""

    def test_create_transaction_valid(self, client):
        """Test creating a valid transaction."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -20.00,
                "currency": "SGD",
                "transaction_date": "2025-12-23",
                "description": "Lunch at cafe",
                "account": "Personal",
                "category": "Food",
                "notes": "Sandwich and coffee"
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["amount"] == -20.00
        assert data["currency"] == "SGD"
        assert data["transaction_date"] == "2025-12-23"
        assert data["description"] == "Lunch at cafe"
        assert data["account"] == "Personal"
        assert data["category"] == "Food"
        assert data["notes"] == "Sandwich and coffee"
        assert data["author"] == "system"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_transaction_minimal(self, client):
        """Test creating transaction with minimal required fields."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -30.00,
                "transaction_date": "2025-12-23",
                "account": "Personal"
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["amount"] == -30.00
        assert data["currency"] == "SGD"  # Default value
        assert data["description"] == ""  # Default value
        assert data["account"] == "Personal"
        assert data["category"] is None
        assert data["notes"] is None

    def test_create_transaction_invalid_data(self, client):
        """Test creating transaction with invalid data."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": "not_a_number",  # Invalid type
                "transaction_date": "2025-12-23",
                "account": "Personal"
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"]["type"] == "ValidationError"

    def test_create_transaction_missing_required_field(self, client):
        """Test creating transaction missing required field."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -20.00,
                "account": "Personal"
                # Missing transaction_date
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestGetTransaction:
    """Tests for GET /api/v1/transactions/{id}"""

    def test_get_transaction_found(self, client):
        """Test getting an existing transaction."""
        # First, get the list to find an ID
        list_response = client.get("/api/v1/transactions")
        transactions = list_response.get_json()
        transaction_id = transactions[0]["id"]

        # Get specific transaction
        response = client.get(f"/api/v1/transactions/{transaction_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == transaction_id
        assert "amount" in data
        assert "currency" in data
        assert "created_at" in data

    def test_get_transaction_not_found(self, client):
        """Test getting a non-existent transaction."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/transactions/{fake_id}")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"]["type"] == "ResourceNotFound"


class TestListTransactions:
    """Tests for GET /api/v1/transactions"""

    def test_list_transactions_default(self, client):
        """Test listing all transactions."""
        response = client.get("/api/v1/transactions")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 5  # 5 transactions from fixture

    def test_list_transactions_with_date_filter(self, client):
        """Test filtering by date range."""
        response = client.get(
            "/api/v1/transactions?start_date=2025-12-21&end_date=2025-12-23"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3  # Transactions from Dec 21-23

    def test_list_transactions_with_account_filter(self, client):
        """Test filtering by account."""
        response = client.get("/api/v1/transactions?account=Personal")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3  # 3 "Personal" transactions
        for tx in data:
            assert tx["account"] == "Personal"

    def test_list_transactions_with_category_filter(self, client):
        """Test filtering by category."""
        response = client.get("/api/v1/transactions?category=Food")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2  # 2 "Food" transactions
        for tx in data:
            assert tx["category"] == "Food"

    def test_list_transactions_with_limit_offset(self, client):
        """Test pagination with limit and offset."""
        # Get first page
        response1 = client.get("/api/v1/transactions?limit=2&offset=0")
        data1 = response1.get_json()
        assert len(data1) == 2

        # Get second page
        response2 = client.get("/api/v1/transactions?limit=2&offset=2")
        data2 = response2.get_json()
        assert len(data2) == 2

        # Ensure different results
        ids1 = {tx["id"] for tx in data1}
        ids2 = {tx["id"] for tx in data2}
        assert ids1.isdisjoint(ids2)

    def test_list_transactions_combined_filters(self, client):
        """Test combining multiple filters."""
        response = client.get(
            "/api/v1/transactions?account=Personal&category=Transport"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2  # 2 Personal/Transport transactions
        for tx in data:
            assert tx["account"] == "Personal"
            assert tx["category"] == "Transport"


class TestUpdateTransaction:
    """Tests for PUT /api/v1/transactions/{id}"""

    def test_update_transaction_full(self, client):
        """Test updating all transaction fields."""
        # Get a transaction ID
        list_response = client.get("/api/v1/transactions")
        transaction_id = list_response.get_json()[0]["id"]

        # Update transaction
        response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            json={
                "amount": -25.00,
                "currency": "USD",
                "transaction_date": "2025-12-24",
                "description": "Updated description",
                "account": "Household",
                "category": "Utilities",
                "notes": "Updated notes"
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["amount"] == -25.00
        assert data["currency"] == "USD"
        assert data["description"] == "Updated description"
        assert data["account"] == "Household"
        assert data["category"] == "Utilities"
        assert data["notes"] == "Updated notes"

    def test_update_transaction_partial(self, client):
        """Test partial update of transaction fields."""
        # Get a transaction ID
        list_response = client.get("/api/v1/transactions")
        transaction_id = list_response.get_json()[0]["id"]

        # Get original data
        original = client.get(f"/api/v1/transactions/{transaction_id}").get_json()

        # Update only amount
        response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            json={"amount": -99.99}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["amount"] == -99.99
        # Other fields should remain unchanged
        assert data["currency"] == original["currency"]
        assert data["description"] == original["description"]

    def test_update_transaction_not_found(self, client):
        """Test updating non-existent transaction."""
        fake_id = str(uuid4())
        response = client.put(
            f"/api/v1/transactions/{fake_id}",
            json={"amount": -50.00}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["type"] == "ResourceNotFound"

    def test_update_transaction_invalid_data(self, client):
        """Test updating with invalid data."""
        # Get a transaction ID
        list_response = client.get("/api/v1/transactions")
        transaction_id = list_response.get_json()[0]["id"]

        response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            json={"amount": "not_a_number"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["type"] == "ValidationError"


class TestDeleteTransaction:
    """Tests for DELETE /api/v1/transactions/{id}"""

    def test_delete_transaction(self, client):
        """Test deleting a transaction (soft delete via superseding)."""
        # Create a transaction to delete
        create_response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -10.00,
                "transaction_date": "2025-12-23",
                "account": "Personal"
            }
        )
        transaction_id = create_response.get_json()["id"]

        # Delete it (soft delete via superseding)
        response = client.delete(f"/api/v1/transactions/{transaction_id}")
        assert response.status_code == 204
        assert response.data == b""

        # Verify transaction still exists but is marked as superseded
        get_response = client.get(f"/api/v1/transactions/{transaction_id}")
        assert get_response.status_code == 200
        data = get_response.get_json()
        assert data["superseded_by"] is not None
        assert data["superseded_at"] is not None

        # Verify it doesn't appear in default list (excludes superseded)
        list_response = client.get("/api/v1/transactions")
        list_data = list_response.get_json()
        assert not any(tx["id"] == transaction_id for tx in list_data)

        # Verify it appears when include_superseded=true
        list_with_superseded = client.get("/api/v1/transactions?include_superseded=true")
        list_data_with = list_with_superseded.get_json()
        assert any(tx["id"] == transaction_id for tx in list_data_with)

    def test_delete_transaction_not_found(self, client):
        """Test deleting non-existent transaction."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/transactions/{fake_id}")

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["type"] == "ResourceNotFound"


class TestLabelEndpoints:
    """Tests for label utility endpoints"""

    def test_list_accounts(self, client):
        """Test listing distinct account labels."""
        response = client.get("/api/v1/transactions/accounts")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert set(data) == {"Household", "Personal"}

    def test_list_categories(self, client):
        """Test listing distinct category labels."""
        response = client.get("/api/v1/transactions/categories")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        # Categories should not include None values
        assert None not in data
        # Should have the categories we set up
        assert "Food" in data
        assert "Transport" in data

    def test_list_labels_empty_database(self, client):
        """Test listing labels when no transactions exist."""
        # Clear all transactions
        with app.app_context():
            from memogarden_core.database import get_db
            db = get_db()
            db.execute("DELETE FROM transactions")
            db.commit()

        # Should return empty arrays
        accounts_response = client.get("/api/v1/transactions/accounts")
        categories_response = client.get("/api/v1/transactions/categories")

        assert accounts_response.status_code == 200
        assert accounts_response.get_json() == []

        assert categories_response.status_code == 200
        assert categories_response.get_json() == []
