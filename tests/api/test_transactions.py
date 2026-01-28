"""Comprehensive API tests for transaction CRUD endpoints."""

import pytest
from datetime import date, datetime, UTC
from uuid import uuid4

from memogarden.main import app
from memogarden.db import get_core


@pytest.fixture(autouse=True)
def setup_database(client):
    """Set up test database with sample data for each test."""
    # Use atomic mode to ensure connection is closed after setup
    with get_core(atomic=True) as core:
        # Create some test transactions - IDs are auto-generated
        # Transaction 1
        entity_id_1 = core.entity.create("transactions")
        core._conn.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_1, -15.50, "SGD", "2025-12-23", "Coffee at Starbucks",
             "Personal", "Food", "system", "Morning coffee")
        )

        # Transaction 2
        entity_id_2 = core.entity.create("transactions")
        core._conn.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_2, -50.00, "SGD", "2025-12-22", "Grocery shopping",
             "Household", "Food", "system", "Weekly groceries")
        )

        # Transaction 3
        entity_id_3 = core.entity.create("transactions")
        core._conn.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_3, -25.00, "SGD", "2025-12-21", "Taxi to airport",
             "Personal", "Transport", "system", "Airport ride")
        )

        # Transaction 4 (no category)
        entity_id_4 = core.entity.create("transactions")
        core._conn.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_4, 1000.00, "SGD", "2025-12-20", "Salary deposit",
             "Household", None, "system", "Monthly salary")
        )

        # Transaction 5 (older date, for filtering tests)
        entity_id_5 = core.entity.create("transactions")
        core._conn.execute(
            """INSERT INTO transactions (
                id, amount, currency, transaction_date, description,
                account, category, author, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id_5, -8.00, "SGD", "2025-11-15", "Bus fare",
             "Personal", "Transport", "system", "Monthly pass")
        )

    # Connection is closed automatically here by context manager

    yield

    # No cleanup needed - client fixture creates fresh temp DB for each test


class TestCreateTransaction:
    """Tests for POST /api/v1/transactions"""

    def test_create_transaction_valid(self, client, auth_headers):
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
            },
            headers=auth_headers
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
        assert data["author"] == "testuser"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_transaction_minimal(self, client, auth_headers):
        """Test creating transaction with minimal required fields."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -30.00,
                "transaction_date": "2025-12-23",
                "account": "Personal"
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["amount"] == -30.00
        assert data["currency"] == "SGD"  # Default value
        assert data["description"] == ""  # Default value
        assert data["account"] == "Personal"
        assert data["category"] is None
        assert data["notes"] is None

    def test_create_transaction_invalid_data(self, client, auth_headers):
        """Test creating transaction with invalid data."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": "not_a_number",  # Invalid type
                "transaction_date": "2025-12-23",
                "account": "Personal"
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["error"]["type"] == "ValidationError"

    def test_create_transaction_missing_required_field(self, client, auth_headers):
        """Test creating transaction missing required field."""
        response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -20.00,
                "account": "Personal"
                # Missing transaction_date
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestGetTransaction:
    """Tests for GET /api/v1/transactions/{id}"""

    def test_get_transaction_found(self, client, auth_headers):
        """Test getting an existing transaction."""
        # First, get the list to find an ID
        list_response = client.get("/api/v1/transactions", headers=auth_headers)
        transactions = list_response.get_json()
        transaction_id = transactions[0]["id"]

        # Get specific transaction
        response = client.get(f"/api/v1/transactions/{transaction_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == transaction_id
        assert "amount" in data
        assert "currency" in data
        assert "created_at" in data

    def test_get_transaction_not_found(self, client, auth_headers):
        """Test getting a non-existent transaction."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/transactions/{fake_id}", headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"]["type"] == "ResourceNotFound"


class TestListTransactions:
    """Tests for GET /api/v1/transactions"""

    def test_list_transactions_default(self, client, auth_headers):
        """Test listing all transactions."""
        response = client.get("/api/v1/transactions", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 5  # 5 transactions from fixture

    def test_list_transactions_with_date_filter(self, client, auth_headers):
        """Test filtering by date range."""
        response = client.get(
            "/api/v1/transactions?start_date=2025-12-21&end_date=2025-12-23",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3  # Transactions from Dec 21-23

    def test_list_transactions_with_account_filter(self, client, auth_headers):
        """Test filtering by account."""
        response = client.get("/api/v1/transactions?account=Personal", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 3  # 3 "Personal" transactions
        for tx in data:
            assert tx["account"] == "Personal"

    def test_list_transactions_with_category_filter(self, client, auth_headers):
        """Test filtering by category."""
        response = client.get("/api/v1/transactions?category=Food", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2  # 2 "Food" transactions
        for tx in data:
            assert tx["category"] == "Food"

    def test_list_transactions_with_limit_offset(self, client, auth_headers):
        """Test pagination with limit and offset."""
        # Get first page
        response1 = client.get("/api/v1/transactions?limit=2&offset=0", headers=auth_headers)
        data1 = response1.get_json()
        assert len(data1) == 2

        # Get second page
        response2 = client.get("/api/v1/transactions?limit=2&offset=2", headers=auth_headers)
        data2 = response2.get_json()
        assert len(data2) == 2

        # Ensure different results
        ids1 = {tx["id"] for tx in data1}
        ids2 = {tx["id"] for tx in data2}
        assert ids1.isdisjoint(ids2)

    def test_list_transactions_combined_filters(self, client, auth_headers):
        """Test combining multiple filters."""
        response = client.get(
            "/api/v1/transactions?account=Personal&category=Transport",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2  # 2 Personal/Transport transactions
        for tx in data:
            assert tx["account"] == "Personal"
            assert tx["category"] == "Transport"


class TestUpdateTransaction:
    """Tests for PUT /api/v1/transactions/{id}"""

    def test_update_transaction_full(self, client, auth_headers):
        """Test updating all transaction fields."""
        # Get a transaction ID
        list_response = client.get("/api/v1/transactions", headers=auth_headers)
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
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["amount"] == -25.00
        assert data["currency"] == "USD"
        assert data["description"] == "Updated description"
        assert data["account"] == "Household"
        assert data["category"] == "Utilities"
        assert data["notes"] == "Updated notes"

    def test_update_transaction_partial(self, client, auth_headers):
        """Test partial update of transaction fields."""
        # Get a transaction ID
        list_response = client.get("/api/v1/transactions", headers=auth_headers)
        transaction_id = list_response.get_json()[0]["id"]

        # Get original data
        original = client.get(f"/api/v1/transactions/{transaction_id}", headers=auth_headers).get_json()

        # Update only amount
        response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            json={"amount": -99.99},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["amount"] == -99.99
        # Other fields should remain unchanged
        assert data["currency"] == original["currency"]
        assert data["description"] == original["description"]

    def test_update_transaction_not_found(self, client, auth_headers):
        """Test updating non-existent transaction."""
        fake_id = str(uuid4())
        response = client.put(
            f"/api/v1/transactions/{fake_id}",
            json={"amount": -50.00},
            headers=auth_headers
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["type"] == "ResourceNotFound"

    def test_update_transaction_invalid_data(self, client, auth_headers):
        """Test updating with invalid data."""
        # Get a transaction ID
        list_response = client.get("/api/v1/transactions", headers=auth_headers)
        transaction_id = list_response.get_json()[0]["id"]

        response = client.put(
            f"/api/v1/transactions/{transaction_id}",
            json={"amount": "not_a_number"},
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["type"] == "ValidationError"


class TestDeleteTransaction:
    """Tests for DELETE /api/v1/transactions/{id}"""

    def test_delete_transaction(self, client, auth_headers):
        """Test deleting a transaction (soft delete via superseding)."""
        # Create a transaction to delete
        create_response = client.post(
            "/api/v1/transactions",
            json={
                "amount": -10.00,
                "transaction_date": "2025-12-23",
                "account": "Personal"
            },
            headers=auth_headers
        )
        transaction_id = create_response.get_json()["id"]

        # Delete it (soft delete via superseding)
        response = client.delete(f"/api/v1/transactions/{transaction_id}", headers=auth_headers)
        assert response.status_code == 204
        assert response.data == b""

        # Verify transaction still exists but is marked as superseded
        get_response = client.get(f"/api/v1/transactions/{transaction_id}", headers=auth_headers)
        assert get_response.status_code == 200
        data = get_response.get_json()
        assert data["superseded_by"] is not None
        assert data["superseded_at"] is not None

        # Verify it doesn't appear in default list (excludes superseded)
        list_response = client.get("/api/v1/transactions", headers=auth_headers)
        list_data = list_response.get_json()
        assert not any(tx["id"] == transaction_id for tx in list_data)

        # Verify it appears when include_superseded=true
        list_with_superseded = client.get("/api/v1/transactions?include_superseded=true", headers=auth_headers)
        list_data_with = list_with_superseded.get_json()
        assert any(tx["id"] == transaction_id for tx in list_data_with)

    def test_delete_transaction_not_found(self, client, auth_headers):
        """Test deleting non-existent transaction."""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/transactions/{fake_id}", headers=auth_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["type"] == "ResourceNotFound"


class TestLabelEndpoints:
    """Tests for label utility endpoints"""

    def test_list_accounts(self, client, auth_headers):
        """Test listing distinct account labels."""
        response = client.get("/api/v1/transactions/accounts", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert set(data) == {"Household", "Personal"}

    def test_list_categories(self, client, auth_headers):
        """Test listing distinct category labels."""
        response = client.get("/api/v1/transactions/categories", headers=auth_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        # Categories should not include None values
        assert None not in data
        # Should have the categories we set up
        assert "Food" in data
        assert "Transport" in data

    def test_list_labels_empty_database(self, client, auth_headers):
        """Test listing labels when no transactions exist."""
        # Clear all transactions
        from memogarden.db import get_core
        core = get_core()
        core._conn.execute("DELETE FROM transactions")
        core._conn.commit()

        # Should return empty arrays
        accounts_response = client.get("/api/v1/transactions/accounts", headers=auth_headers)
        categories_response = client.get("/api/v1/transactions/categories", headers=auth_headers)

        assert accounts_response.status_code == 200
        assert accounts_response.get_json() == []

        assert categories_response.status_code == 200
        assert categories_response.get_json() == []
