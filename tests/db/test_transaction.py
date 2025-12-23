"""Tests for db/transaction.py TransactionOperations class."""

import pytest
from datetime import date

from memogarden_core.db.transaction import TransactionOperations
from memogarden_core.db.entity import EntityOperations
from memogarden_core.db import Core
from memogarden_core.exceptions import ResourceNotFound


class TestTransactionGetById:
    """Tests for TransactionOperations.get_by_id() method."""

    def test_get_by_id_returns_transaction_for_existing_id(self, test_db):
        """get_by_id() should return transaction for existing ID."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db, core=None)

        # Create entity first
        entity_id = entity_ops.create("transactions")

        # Manually insert transaction (since we don't have Core reference)
        test_db.execute(
            """INSERT INTO transactions
               (id, amount, currency, transaction_date, description, account, author)
               VALUES (?, 100.50, 'SGD', '2025-12-23', 'Test transaction', 'Household', 'system')""",
            (entity_id,)
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
        txn_ops = TransactionOperations(test_db, core=None)

        with pytest.raises(ResourceNotFound) as exc_info:
            txn_ops.get_by_id("non-existent-id")

        assert "non-existent-id" in str(exc_info.value.message)
        assert exc_info.value.details == {"transaction_id": "non-existent-id"}

    def test_get_by_id_returns_full_view_data(self, test_db):
        """get_by_id() should return all fields from transactions_view."""
        entity_ops = EntityOperations(test_db)
        txn_ops = TransactionOperations(test_db, core=None)

        entity_id = entity_ops.create("transactions")

        test_db.execute(
            """INSERT INTO transactions
               (id, amount, currency, transaction_date, description, account, category, notes, author)
               VALUES (?, 50.0, 'SGD', '2025-12-23', 'Coffee', 'Personal', 'Food', 'Morning coffee', 'system')""",
            (entity_id,)
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
        """create() should insert transaction with correct values using Core API."""
        core = Core(test_db, atomic=False)
        transaction_id = core.transaction.create(
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
            (transaction_id,)
        ).fetchone()

        assert row["id"] == transaction_id
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
        core = Core(test_db, atomic=False)
        transaction_id = core.transaction.create(
            amount=75.0,
            transaction_date=date(2025, 12, 23),
            description="Test",
            account="Personal",
            category=None,
            notes=None
        )

        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row["category"] is None
        assert row["notes"] is None

    def test_create_with_custom_author(self, test_db):
        """create() should use custom author when provided."""
        core = Core(test_db, atomic=False)
        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Test",
            account="Household",
            author="user@example.com"
        )

        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row["author"] == "user@example.com"

    def test_create_converts_date_to_string(self, test_db):
        """create() should convert date to ISO 8601 date string."""
        core = Core(test_db, atomic=False)
        test_date = date(2025, 6, 15)

        transaction_id = core.transaction.create(
            amount=50.0,
            transaction_date=test_date,
            description="Test",
            account="Personal"
        )

        row = test_db.execute(
            "SELECT transaction_date FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row["transaction_date"] == "2025-06-15"

    def test_create_without_core_raises_value_error(self, test_db):
        """create() without Core reference should raise ValueError."""
        txn_ops = TransactionOperations(test_db, core=None)

        with pytest.raises(ValueError, match="requires Core reference"):
            txn_ops.create(
                amount=100.0,
                transaction_date=date(2025, 12, 23),
                description="Test",
                account="Personal"
            )

    def test_create_generates_unique_ids(self, test_db):
        """create() should generate unique IDs for multiple transactions."""
        core = Core(test_db, atomic=False)

        ids = []
        for i in range(5):
            txn_id = core.transaction.create(
                amount=10.0 * i,
                transaction_date=date(2025, 12, 23),
                description=f"Transaction {i}",
                account="Test"
            )
            ids.append(txn_id)

        # All IDs should be unique
        assert len(set(ids)) == 5

        # All should exist in database
        for txn_id in ids:
            row = test_db.execute(
                "SELECT * FROM transactions WHERE id = ?",
                (txn_id,)
            ).fetchone()
            assert row is not None

    def test_create_also_creates_entity_registry_entry(self, test_db):
        """create() should also create entity registry entry."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Test",
            account="Household"
        )

        # Verify entity registry entry exists
        entity_row = test_db.execute(
            "SELECT * FROM entity WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert entity_row is not None
        assert entity_row["type"] == "transactions"


class TestTransactionList:
    """Tests for TransactionOperations.list() method."""

    def test_list_returns_all_transactions_no_filters(self, test_db):
        """list() should return all transactions when no filters provided."""
        core = Core(test_db, atomic=False)

        # Create multiple transactions
        ids = []
        for i in range(3):
            txn_id = core.transaction.create(
                amount=10.0 * (i + 1),
                transaction_date=date(2025, 12, 20 + i),
                description=f"Transaction {i}",
                account="Household"
            )
            ids.append(txn_id)

        # List all
        rows = core.transaction.list({})

        assert len(rows) == 3
        # Should be ordered by date DESC, created_at DESC
        assert rows[0]["description"] == "Transaction 2"

    def test_list_filters_by_account(self, test_db):
        """list() should filter by account."""
        core = Core(test_db, atomic=False)

        # Create transactions with different accounts
        core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Household txn",
            account="Household"
        )

        core.transaction.create(
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Personal txn",
            account="Personal"
        )

        # Filter by account
        rows = core.transaction.list({"account": "Household"})

        assert len(rows) == 1
        assert rows[0]["account"] == "Household"

    def test_list_filters_by_category(self, test_db):
        """list() should filter by category."""
        core = Core(test_db, atomic=False)

        # Create transactions with different categories
        core.transaction.create(
            amount=20.0,
            transaction_date=date(2025, 12, 23),
            description="Food",
            account="Personal",
            category="Food"
        )

        core.transaction.create(
            amount=10.0,
            transaction_date=date(2025, 12, 23),
            description="Transport",
            account="Personal",
            category="Transport"
        )

        # Filter by category
        rows = core.transaction.list({"category": "Food"})

        assert len(rows) == 1
        assert rows[0]["category"] == "Food"

    def test_list_filters_by_date_range(self, test_db):
        """list() should filter by date range."""
        core = Core(test_db, atomic=False)

        # Create transactions on different dates
        core.transaction.create(
            amount=50.0,
            transaction_date=date(2025, 12, 10),
            description="Early",
            account="Personal"
        )

        core.transaction.create(
            amount=75.0,
            transaction_date=date(2025, 12, 15),
            description="Middle",
            account="Personal"
        )

        core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 20),
            description="Late",
            account="Personal"
        )

        # Filter by date range
        rows = core.transaction.list({
            "start_date": "2025-12-12",
            "end_date": "2025-12-18"
        })

        assert len(rows) == 1
        assert rows[0]["description"] == "Middle"

    def test_list_excludes_superseded_by_default(self, test_db):
        """list() should exclude superseded transactions by default."""
        core = Core(test_db, atomic=False)

        # Create active transaction
        active_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Active",
            account="Personal"
        )

        # Create superseded transaction
        old_id = core.transaction.create(
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Old",
            account="Personal"
        )
        core.entity.supersede(old_id, active_id)

        # List should exclude superseded
        rows = core.transaction.list({})

        assert len(rows) == 1
        assert rows[0]["id"] == active_id

    def test_list_includes_superseded_when_flag_set(self, test_db):
        """list() should include superseded transactions when flag is True."""
        core = Core(test_db, atomic=False)

        # Create transactions
        active_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Active",
            account="Personal"
        )

        old_id = core.transaction.create(
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Old",
            account="Personal"
        )
        core.entity.supersede(old_id, active_id)

        # Include superseded
        rows = core.transaction.list({"include_superseded": True})

        assert len(rows) == 2
        ids = {row["id"] for row in rows}
        assert active_id in ids
        assert old_id in ids

    def test_list_with_limit_and_offset(self, test_db):
        """list() should support limit and offset."""
        core = Core(test_db, atomic=False)

        # Create 5 transactions
        for i in range(5):
            core.transaction.create(
                amount=10.0 * i,
                transaction_date=date(2025, 12, 20 + i),
                description=f"Transaction {i}",
                account="Personal"
            )

        # Test limit
        rows = core.transaction.list({}, limit=2)
        assert len(rows) == 2

        # Test offset
        rows = core.transaction.list({}, limit=2, offset=2)
        assert len(rows) == 2

    def test_list_with_combined_filters(self, test_db):
        """list() should combine multiple filters correctly."""
        core = Core(test_db, atomic=False)

        # Create various transactions
        core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 10),
            description="Household Food",
            account="Household",
            category="Food"
        )

        core.transaction.create(
            amount=50.0,
            transaction_date=date(2025, 12, 15),
            description="Household Transport",
            account="Household",
            category="Transport"
        )

        core.transaction.create(
            amount=75.0,
            transaction_date=date(2025, 12, 12),
            description="Personal Food",
            account="Personal",
            category="Food"
        )

        # Filter by account AND date range
        rows = core.transaction.list({
            "account": "Household",
            "start_date": "2025-12-12"
        })

        assert len(rows) == 1
        assert rows[0]["description"] == "Household Transport"


class TestTransactionUpdate:
    """Tests for TransactionOperations.update() method."""

    def test_update_updates_only_provided_fields(self, test_db):
        """update() should update only the fields provided."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household",
            category="Food"
        )

        # Update only amount and description
        core.transaction.update(transaction_id, {
            "amount": 200.0,
            "description": "Updated"
        })

        # Verify
        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row["amount"] == 200.0
        assert row["description"] == "Updated"
        assert row["account"] == "Household"  # Unchanged
        assert row["category"] == "Food"  # Unchanged

    def test_update_handles_none_values_correctly(self, test_db):
        """update() should not update fields with None values."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household",
            category="Food",
            notes="Some notes"
        )

        # Update with None values - should not update those fields
        core.transaction.update(transaction_id, {
            "amount": 150.0,
            "category": None,
            "notes": None
        })

        row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row["amount"] == 150.0
        assert row["category"] == "Food"  # Unchanged (None not updated)
        assert row["notes"] == "Some notes"  # Unchanged

    def test_update_excludes_id_field(self, test_db):
        """update() should exclude 'id' field from updates."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Try to update with id included
        core.transaction.update(transaction_id, {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "amount": 200.0
        })

        # ID should not change
        row = test_db.execute(
            "SELECT id FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row is not None  # Original ID still exists

    def test_update_converts_date_to_string(self, test_db):
        """update() should convert date to ISO 8601 date string."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Update with date object
        new_date = date(2025, 6, 15)
        core.transaction.update(transaction_id, {"transaction_date": new_date})

        row = test_db.execute(
            "SELECT transaction_date FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert row["transaction_date"] == "2025-06-15"

    def test_update_updates_entity_updated_at(self, test_db):
        """update() should update entity.updated_at timestamp."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Get original updated_at
        original_row = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (transaction_id,)
        ).fetchone()
        original_updated_at = original_row["updated_at"]

        # Wait a tiny bit to ensure timestamp changes
        import time
        time.sleep(0.001)

        # Update transaction
        core.transaction.update(transaction_id, {"amount": 200.0})

        # Check updated_at changed
        updated_row = test_db.execute(
            "SELECT updated_at FROM entity WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert updated_row["updated_at"] != original_updated_at

    def test_update_with_empty_dict_does_nothing(self, test_db):
        """update() should do nothing when data dict is empty."""
        core = Core(test_db, atomic=False)

        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Original",
            account="Household"
        )

        # Get original values
        original_row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        # Update with empty dict
        core.transaction.update(transaction_id, {})

        # Verify nothing changed
        updated_row = test_db.execute(
            "SELECT * FROM transactions WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        assert original_row["amount"] == updated_row["amount"]
        assert original_row["description"] == updated_row["description"]


class TestTransactionIntegration:
    """Integration tests for TransactionOperations."""

    def test_full_transaction_lifecycle(self, test_db):
        """Test complete lifecycle: create, get, list, update."""
        core = Core(test_db, atomic=False)

        # Create
        transaction_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Test transaction",
            account="Household",
            category="Food"
        )

        # Get
        row = core.transaction.get_by_id(transaction_id)
        assert row["amount"] == 100.0

        # List
        rows = core.transaction.list({"account": "Household"})
        assert len(rows) == 1

        # Update
        core.transaction.update(transaction_id, {"amount": 200.0})
        row = core.transaction.get_by_id(transaction_id)
        assert row["amount"] == 200.0

    def test_list_with_superseded_transactions(self, test_db):
        """Test listing with mix of active and superseded transactions."""
        core = Core(test_db, atomic=False)

        # Create active transaction
        active_id = core.transaction.create(
            amount=100.0,
            transaction_date=date(2025, 12, 23),
            description="Active",
            account="Personal"
        )

        # Create old transaction and supersede
        old_id = core.transaction.create(
            amount=50.0,
            transaction_date=date(2025, 12, 23),
            description="Old version",
            account="Personal"
        )
        core.entity.supersede(old_id, active_id)

        # List without superseded
        active_only = core.transaction.list({})
        assert len(active_only) == 1
        assert active_only[0]["id"] == active_id

        # List with superseded
        all_txns = core.transaction.list({"include_superseded": True})
        assert len(all_txns) == 2
