"""Tests for db/transaction.py TransactionOperations class."""

import pytest
from datetime import date

from memogarden_core.db.transaction import TransactionOperations
from memogarden_core.db.entity import EntityOperations
from memogarden_core.exceptions import ResourceNotFound


class TestTransactionGetById:
    """Tests for TransactionOperations.get_by_id() method."""

    def test_get_by_id_returns_transaction_for_existing_id(self, test_db):
        """get_by_id() should return transaction for existing ID."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create entity first
        entity_id = entity_ops.create("transactions")

        # Create transaction
        txn_ops.create(
            entity_id,
            amount=100.50,
            transaction_date=date(2025, 12, 23),
            description="Test transaction",
            account="Household"
        )

        # Get by ID
        row = txn_ops.get_by_id(entity_id)

        assert row is not None
        assert row["id"] == entity_id
        assert row["amount"] == 100.50
        assert row["transaction_date"] == "2025-12-23"
        assert row["description"] == "Test transaction"
        assert row["account"] == "Household"

    def test_get_by_id_raises_resource_not_found_for_non_existent(self, test_db):
        """get_by_id() should raise ResourceNotFound for non-existent ID."""
        txn_ops = TransactionOperations(test_db)

        with pytest.raises(ResourceNotFound) as exc_info:
            txn_ops.get_by_id("non-existent-id")

        assert "non-existent-id" in str(exc_info.value.message)
        assert exc_info.value.details == {"transaction_id": "non-existent-id"}

    def test_get_by_id_returns_full_view_data(self, test_db):
        """get_by_id() should return all fields from transactions_view."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")

        txn_ops.create(
            entity_id,
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Coffee",
            account="Personal",
            category="Food",
            notes="Morning coffee"
        )

        row = txn_ops.get_by_id(entity_id)

        # Check entity metadata fields
        assert "created_at" in row.keys()
        assert "updated_at" in row.keys()
        assert row["superseded_by"] is None
        assert "group_id" in row.keys()
        assert "derived_from" in row.keys()

        # Check transaction fields
        assert row["amount"] == 50.0
        assert row["currency"] == "SGD"
        assert row["category"] == "Food"
        assert row["notes"] == "Morning coffee"


class TestTransactionCreate:
    """Tests for TransactionOperations.create() method."""

    def test_create_inserts_transaction_with_correct_values(self, test_db):
        """create() should insert transaction with correct values."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        entity_ops.create("transactions", entity_id=entity_id)

        txn_ops.create(
            entity_id,
            amount=123.45,
            transaction_date=date(2025, 12, 23),
            description="Grocery shopping",
            account="Household",
            category="Groceries",
            notes="Weekly groceries"
        )

        # Verify in database
        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["id"] == entity_id
        assert row["amount"] == 123.45
        assert row["currency"] == "SGD"
        assert row["transaction_date"] == "2025-12-23"
        assert row["description"] == "Grocery shopping"
        assert row["account"] == "Household"
        assert row["category"] == "Groceries"
        assert row["notes"] == "Weekly groceries"
        assert row["author"] == "system"

    def test_create_with_optional_params_none(self, test_db):
        """create() should handle None values for optional params."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")

        txn_ops.create(
            entity_id,
            amount=75.0,
            transaction_date=date(2025, 12, 23),
            description="Test",
            account="Personal",
            category=None,
            notes=None
        )

        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["category"] is None
        assert row["notes"] is None

    def test_create_with_custom_author(self, test_db):
        """create() should use custom author when provided."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")

        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Test",
            account="Household",
            author="user@example.com"
        )

        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["author"] == "user@example.com"

    def test_create_with_date_conversion(self, test_db):
        """create() should convert date to ISO 8601 date string."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        test_date = date(2025, 6, 15)

        txn_ops.create(
            entity_id,
            amount=50.0,
            transaction_date=test_date,
            description="Test",
            account="Personal"
        )

        row = test_db.execute(
            "SELECT transaction_date FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["transaction_date"] == "2025-06-15"


class TestTransactionList:
    """Tests for TransactionOperations.list() method."""

    def test_list_returns_all_transactions_no_filters(self, test_db):
        """list() should return all transactions when no filters provided."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create multiple transactions
        ids = []
        for i in range(3):
            entity_id = entity_ops.create("transactions")
            ids.append(entity_id)
            txn_ops.create(
                entity_id,
                amount=10.0 * (i + 1),
                transaction_date=date(2025, 12, 20 + i),
                description=f"Transaction {i}",
                account="Household"
            )

        # List all
        rows = txn_ops.list({})

        assert len(rows) == 3
        # Should be ordered by date DESC, created_at DESC
        assert rows[0]["description"] == "Transaction 2"
        assert rows[1]["description"] == "Transaction 1"
        assert rows[2]["description"] == "Transaction 0"

    def test_list_filters_by_account(self, test_db):
        """list() should filter by account."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create transactions with different accounts
        household_id = entity_ops.create("transactions")
        txn_ops.create(
            household_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Household txn",
            account="Household"
        )

        personal_id = entity_ops.create("transactions")
        txn_ops.create(
            personal_id,
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Personal txn",
            account="Personal"
        )

        # Filter by account
        rows = txn_ops.list({"account": "Household"})

        assert len(rows) == 1
        assert rows[0]["account"] == "Household"

    def test_list_filters_by_category(self, test_db):
        """list() should filter by category."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create transactions with different categories
        food_id = entity_ops.create("transactions")
        txn_ops.create(
            food_id,
            amount=20.0,
            transaction_date=date(2025, 12, 23),
            description="Food",
            account="Personal",
            category="Food"
        )

        transport_id = entity_ops.create("transactions")
        txn_ops.create(
            transport_id,
            amount=10.0,
            transaction_date=date(2025, 12, 23),
            description="Transport",
            account="Personal",
            category="Transport"
        )

        # Filter by category
        rows = txn_ops.list({"category": "Food"})

        assert len(rows) == 1
        assert rows[0]["category"] == "Food"

    def test_list_filters_by_date_range(self, test_db):
        """list() should filter by date range."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create transactions on different dates
        early_id = entity_ops.create("transactions")
        txn_ops.create(
            early_id,
            amount=50.0,
            transaction_date=date(2025, 12, 10),
            description="Early",
            account="Personal"
        )

        middle_id = entity_ops.create("transactions")
        txn_ops.create(
            middle_id,
            amount=75.0,
            transaction_date=date(2025, 12, 15),
            description="Middle",
            account="Personal"
        )

        late_id = entity_ops.create("transactions")
        txn_ops.create(
            late_id,
            amount=100.0,
            transaction_date=date(2025, 12, 20),
            description="Late",
            account="Personal"
        )

        # Filter by date range
        rows = txn_ops.list({
            "start_date": "2025-12-12",
            "end_date": "2025-12-18"
        })

        assert len(rows) == 1
        assert rows[0]["description"] == "Middle"

    def test_list_excludes_superseded_by_default(self, test_db):
        """list() should exclude superseded transactions by default."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create active transaction
        active_id = entity_ops.create("transactions")
        txn_ops.create(
            active_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Active",
            account="Personal"
        )

        # Create superseded transaction
        old_id = entity_ops.create("transactions")
        txn_ops.create(
            old_id,
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Old",
            account="Personal"
        )
        entity_ops.supersede(old_id, active_id)

        # List should exclude superseded
        rows = txn_ops.list({})

        assert len(rows) == 1
        assert rows[0]["id"] == active_id

    def test_list_includes_superseded_when_flag_set(self, test_db):
        """list() should include superseded transactions when flag is True."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create transactions
        active_id = entity_ops.create("transactions")
        txn_ops.create(
            active_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Active",
            account="Personal"
        )

        old_id = entity_ops.create("transactions")
        txn_ops.create(
            old_id,
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Old",
            account="Personal"
        )
        entity_ops.supersede(old_id, active_id)

        # Include superseded
        rows = txn_ops.list({"include_superseded": True})

        assert len(rows) == 2
        ids = {row["id"] for row in rows}
        assert active_id in ids
        assert old_id in ids

    def test_list_with_limit_and_offset(self, test_db):
        """list() should respect limit and offset parameters."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create 5 transactions
        ids = []
        for i in range(5):
            entity_id = entity_ops.create("transactions")
            ids.append(entity_id)
            txn_ops.create(
                entity_id,
                amount=10.0 * i,
                transaction_date=date(2025, 12, 20 + i),
                description=f"Transaction {i}",
                account="Personal"
            )

        # Test limit
        rows = txn_ops.list({}, limit=2)
        assert len(rows) == 2

        # Test offset
        rows = txn_ops.list({}, limit=2, offset=2)
        assert len(rows) == 2
        # Should skip first 2 (ids[4] and ids[3] due to DESC ordering)
        returned_ids = {row["id"] for row in rows}
        assert ids[2] in returned_ids
        assert ids[1] in returned_ids

    def test_list_with_combined_filters(self, test_db):
        """list() should combine multiple filters correctly."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create various transactions
        txn1_id = entity_ops.create("transactions")
        txn_ops.create(
            txn1_id,
            amount=100.0,
            transaction_date=date(2025, 12, 10),
            description="Household Food",
            account="Household",
            category="Food"
        )

        txn2_id = entity_ops.create("transactions")
        txn_ops.create(
            txn2_id,
            amount=50.0,
            transaction_date=date(2025, 12, 15),
            description="Household Transport",
            account="Household",
            category="Transport"
        )

        txn3_id = entity_ops.create("transactions")
        txn_ops.create(
            txn3_id,
            amount=75.0,
            transaction_date=date(2025, 12, 12),
            description="Personal Food",
            account="Personal",
            category="Food"
        )

        # Filter by account AND date range
        rows = txn_ops.list({
            "account": "Household",
            "start_date": "2025-12-12"
        })

        assert len(rows) == 1
        assert rows[0]["id"] == txn2_id


class TestTransactionUpdate:
    """Tests for TransactionOperations.update() method."""

    def test_update_updates_only_provided_fields(self, test_db):
        """update() should update only the fields provided."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household",
            category="Food"
        )

        # Update only amount and description
        txn_ops.update(entity_id, {
            "amount": 200.0,
            "description": "Updated"
        })

        # Verify updates
        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["amount"] == 200.0
        assert row["description"] == "Updated"
        assert row["account"] == "Household"  # Unchanged
        assert row["category"] == "Food"  # Unchanged

    def test_update_handles_none_values_correctly(self, test_db):
        """update() should not update fields with None values."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household",
            category="Food",
            notes="Some notes"
        )

        # Update with None values - should not update those fields
        txn_ops.update(entity_id, {
            "amount": 150.0,
            "category": None,
            "notes": None
        })

        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["amount"] == 150.0
        assert row["category"] == "Food"  # Unchanged (None was ignored)
        assert row["notes"] == "Some notes"  # Unchanged (None was ignored)

    def test_update_excludes_id_field(self, test_db):
        """update() should exclude 'id' field from updates."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Try to update with id included
        txn_ops.update(entity_id, {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "amount": 200.0
        })

        # ID should not change
        row = test_db.execute(
            "SELECT id, amount FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["id"] == entity_id  # Unchanged
        assert row["amount"] == 200.0  # Updated

    def test_update_converts_date_to_string(self, test_db):
        """update() should convert date to ISO 8601 date string."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Update with date object
        new_date = date(2025, 6, 15)
        txn_ops.update(entity_id, {"transaction_date": new_date})

        row = test_db.execute(
            "SELECT transaction_date FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        assert row["transaction_date"] == "2025-06-15"

    def test_update_updates_entity_updated_at(self, test_db):
        """update() should update entity.updated_at timestamp."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Get original updated_at
        original_row = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (entity_id,)
        ).fetchone()
        original_updated_at = original_row["updated_at"]

        # Update transaction
        txn_ops.update(entity_id, {"amount": 200.0})

        # Check updated_at changed
        updated_row = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (entity_id,)
        ).fetchone()
        assert updated_row["updated_at"] != original_updated_at

    def test_update_with_empty_dict_does_nothing(self, test_db):
        """update() should do nothing when data dict is empty."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Get original values
        original_row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()

        # Update with empty dict
        txn_ops.update(entity_id, {})

        # Verify nothing changed
        updated_row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (entity_id,)
        ).fetchone()
        assert original_row["amount"] == updated_row["amount"]
        assert original_row["description"] == updated_row["description"]


class TestTransactionIntegration:
    """Integration tests for TransactionOperations."""

    def test_full_transaction_lifecycle(self, test_db):
        """Test complete lifecycle: create, get, list, update."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create
        entity_id = entity_ops.create("transactions")
        txn_ops.create(
            entity_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Test transaction",
            account="Household",
            category="Food"
        )

        # Get
        row = txn_ops.get_by_id(entity_id)
        assert row["amount"] == 100.0

        # List
        rows = txn_ops.list({"account": "Household"})
        assert len(rows) == 1
        assert rows[0]["id"] == entity_id

        # Update
        txn_ops.update(entity_id, {"amount": 150.0})
        row = txn_ops.get_by_id(entity_id)
        assert row["amount"] == 150.0

    def test_list_with_superseded_transactions(self, test_db):
        """Test listing with mix of active and superseded transactions."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db)

        # Create active transaction
        active_id = entity_ops.create("transactions")
        txn_ops.create(
            active_id,
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Active",
            account="Personal"
        )

        # Create old transaction and supersede
        old_id = entity_ops.create("transactions")
        txn_ops.create(
            old_id,
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Old version",
            account="Personal"
        )
        entity_ops.supersede(old_id, active_id)

        # List without superseded
        active_only = txn_ops.list({})
        assert len(active_only) == 1
        assert active_only[0]["id"] == active_id

        # List with superseded
        all_txns = txn_ops.list({"include_superseded": True})
        assert len(all_txns) == 2
