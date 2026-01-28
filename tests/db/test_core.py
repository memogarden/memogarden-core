"""Tests for Core API database interface.

Behavior-focused tests using real in-memory SQLite.
No mocks - testing observable behavior.
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import date
from memogarden.db import get_core, Core, _create_connection
from memogarden.exceptions import ResourceNotFound


# ============================================================================
# _create_connection tests
# ============================================================================

def test_create_connection_returns_connection():
    """_create_connection() should return a valid SQLite connection."""
    conn = _create_connection()
    assert conn is not None
    assert isinstance(conn, sqlite3.Connection)
    assert conn.row_factory == sqlite3.Row
    conn.close()


def test_create_connection_enables_foreign_keys():
    """_create_connection() should enable foreign key constraints."""
    conn = _create_connection()
    # Verify foreign keys are enabled
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1  # 1 = enabled
    conn.close()


# ============================================================================
# get_core() tests
# ============================================================================

def test_get_core_autocommit_mode():
    """get_core(atomic=False) should return Core instance."""
    core = get_core(atomic=False)
    assert core is not None
    assert isinstance(core, Core)
    assert core._atomic is False


def test_get_core_atomic_mode():
    """get_core(atomic=True) should return Core instance."""
    core = get_core(atomic=True)
    assert core is not None
    assert isinstance(core, Core)
    assert core._atomic is True


# ============================================================================
# Core.entity property tests
# ============================================================================

def test_core_entity_property_returns_entity_operations(test_db):
    """Core.entity should return EntityOperations instance."""
    # Need to create a schema for the entity operations to work
    core = Core(test_db, atomic=False)
    entity_ops = core.entity
    assert entity_ops is not None
    assert hasattr(entity_ops, 'create')
    assert hasattr(entity_ops, 'get_by_id')
    assert hasattr(entity_ops, 'supersede')


def test_core_entity_property_is_cached(test_db):
    """Core.entity should cache EntityOperations instance."""
    core = Core(test_db, atomic=False)
    entity_ops1 = core.entity
    entity_ops2 = core.entity
    assert entity_ops1 is entity_ops2  # Same instance


# ============================================================================
# Core.transaction property tests
# ============================================================================

def test_core_transaction_property_returns_transaction_operations(test_db):
    """Core.transaction should return TransactionOperations instance."""
    core = Core(test_db, atomic=False)
    tx_ops = core.transaction
    assert tx_ops is not None
    assert hasattr(tx_ops, 'get_by_id')
    assert hasattr(tx_ops, 'create')
    assert hasattr(tx_ops, 'list')
    assert hasattr(tx_ops, 'update')


def test_core_transaction_property_is_cached(test_db):
    """Core.transaction should cache TransactionOperations instance."""
    core = Core(test_db, atomic=False)
    tx_ops1 = core.transaction
    tx_ops2 = core.transaction
    assert tx_ops1 is tx_ops2  # Same instance


# ============================================================================
# Core context manager tests (atomic mode)
# ============================================================================

def test_core_atomic_context_manager_enters(test_db):
    """Core with atomic=True should work as context manager."""
    core = Core(test_db, atomic=True)
    with core as ctx:
        assert ctx is core


def test_core_atomic_context_manager_commits_on_success():
    """Core context manager should commit on successful exit."""
    # Use file-based database so we can open a new connection to verify
    import tempfile
    import os

    # Create temp database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        # Create initial entity
        conn1 = sqlite3.connect(db_path)
        conn1.row_factory = sqlite3.Row
        conn1.execute("PRAGMA foreign_keys = ON")
        core1 = Core(conn1, atomic=True)
        entity_id_1 = core1.entity.create("transactions")
        conn1.commit()
        conn1.close()

        # Use context manager for transaction
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        conn2.execute("PRAGMA foreign_keys = ON")
        with Core(conn2, atomic=True) as tx_core:
            entity_id_2 = tx_core.entity.create("transactions")
        # Connection closed on exit

        # Verify both entities exist (committed) using fresh connection
        conn3 = sqlite3.connect(db_path)
        conn3.row_factory = sqlite3.Row
        rows = conn3.execute("SELECT * FROM entity").fetchall()
        conn3.close()

        assert len(rows) == 2
    finally:
        # Cleanup
        os.unlink(db_path)


def test_core_atomic_context_manager_rolls_back_on_exception():
    """Core context manager should rollback on exception."""
    import tempfile
    import os

    # Create temp database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        # Create initial entity
        conn1 = sqlite3.connect(db_path)
        conn1.row_factory = sqlite3.Row
        conn1.execute("PRAGMA foreign_keys = ON")
        core1 = Core(conn1, atomic=True)
        entity_id = core1.entity.create("transactions")
        conn1.commit()
        conn1.close()

        # Get initial count
        conn_check = sqlite3.connect(db_path)
        conn_check.row_factory = sqlite3.Row
        initial_count = len(conn_check.execute("SELECT * FROM entity").fetchall())
        conn_check.close()

        # Try to create entity but raise exception
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        conn2.execute("PRAGMA foreign_keys = ON")
        try:
            with Core(conn2, atomic=True) as tx_core:
                tx_core.entity.create("transactions")
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Verify count unchanged (rolled back)
        conn3 = sqlite3.connect(db_path)
        conn3.row_factory = sqlite3.Row
        final_count = len(conn3.execute("SELECT * FROM entity").fetchall())
        conn3.close()

        assert final_count == initial_count
    finally:
        # Cleanup
        os.unlink(db_path)


def test_core_atomic_context_manager_closes_connection(test_db):
    """Core context manager should close connection on exit."""
    core = Core(test_db, atomic=True)
    conn_id = id(core._conn)

    with core:
        pass  # Normal exit

    # Connection should be closed
    # Note: We can't directly test if connection is closed without accessing
    # private attributes, but we can verify behavior
    # Attempting to use the connection after exit should fail
    with pytest.raises(Exception):
        core._conn.execute("SELECT 1")


def test_core_non_atomic_raises_runtime_error_without_context_manager(test_db):
    """Core with atomic=False should raise RuntimeError when used as context manager."""
    core = Core(test_db, atomic=False)
    with pytest.raises(RuntimeError, match="atomic=True"):
        with core:
            pass


def test_core_atomic_mode_without_context_manager_raises_runtime_error(test_db):
    """Core with atomic=True should raise RuntimeError if __enter__ called directly."""
    core = Core(test_db, atomic=False)
    # atomic=False Core should not be used as context manager
    with pytest.raises(RuntimeError, match="atomic=True"):
        with core:
            pass


# ============================================================================
# Core __del__ cleanup tests
# ============================================================================

def test_core_del_closes_connection():
    """Core.__del__ should close connection if still open."""
    core = get_core(atomic=False)
    conn = core._conn

    # Verify connection is open
    assert conn is not None

    # Delete core object
    del core

    # Connection should be closed (we can't directly test this without
    # accessing the connection after deletion, which would cause issues)
    # This test mainly ensures __del__ doesn't raise an exception


# ============================================================================
# Integration tests: Core API with real operations
# ============================================================================

def test_core_autocommit_single_operation():
    """Core with atomic=False should work for single operations."""
    # Use in-memory database for this test
    core = get_core(atomic=False)
    # Can't directly test without schema, so we verify the interface exists
    assert hasattr(core, 'entity')
    assert hasattr(core, 'transaction')


def test_core_atomic_multi_operation_transaction():
    """Core with atomic=True should commit multiple operations together."""
    import tempfile
    import os

    # Create temp database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        entity_id_1 = None
        entity_id_2 = None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        with Core(conn, atomic=True) as core:
            # Create first entity
            entity_id_1 = core.entity.create("transactions")

            # Create second entity
            entity_id_2 = core.entity.create("transactions")

            # Both should be created in same transaction

        # Verify both entities exist after commit (using new connection)
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        rows = conn2.execute("SELECT * FROM entity").fetchall()
        ids = [row['id'] for row in rows]
        conn2.close()

        assert entity_id_1 in ids
        assert entity_id_2 in ids
    finally:
        os.unlink(db_path)


def test_core_atomic_transaction_rolls_back_all_on_error():
    """Core with atomic=True should rollback all operations on error."""
    import tempfile
    import os

    # Create temp database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        # Get initial count
        conn_check = sqlite3.connect(db_path)
        conn_check.row_factory = sqlite3.Row
        initial_count = len(conn_check.execute("SELECT * FROM entity").fetchall())
        conn_check.close()

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            with Core(conn, atomic=True) as core:
                # Create entity
                core.entity.create("transactions")

                # Create another entity
                core.entity.create("transactions")

                # Raise exception to trigger rollback
                raise RuntimeError("Intentional error")
        except RuntimeError:
            pass

        # Verify no entities were created (all rolled back)
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        final_count = len(conn2.execute("SELECT * FROM entity").fetchall())
        conn2.close()

        assert final_count == initial_count
    finally:
        os.unlink(db_path)


# ============================================================================
# EntityOperations integration tests via Core
# ============================================================================

def test_core_entity_create_generates_uuid(test_db):
    """core.entity.create() should generate valid UUID."""
    entity_id = None
    with Core(test_db, atomic=True) as core:
        entity_id = core.entity.create("transactions")
        # Verify within context (before connection closes)

    assert entity_id is not None
    assert len(entity_id) == 36  # UUID format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    assert entity_id.count("-") == 4


def test_core_entity_get_by_id_returns_entity():
    """core.entity.get_by_id() should return entity row."""
    import tempfile
    import os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        # Create entity
        conn1 = sqlite3.connect(db_path)
        conn1.row_factory = sqlite3.Row
        conn1.execute("PRAGMA foreign_keys = ON")
        with Core(conn1, atomic=True) as core:
            entity_id = core.entity.create("transactions")

        # Get the entity with fresh connection
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        core2 = Core(conn2, atomic=False)
        row = core2.entity.get_by_id(entity_id)

        assert row is not None
        assert row['id'] == entity_id
        assert row['type'] == 'transactions'
    finally:
        os.unlink(db_path)


def test_core_entity_get_by_id_raises_not_found(test_db):
    """core.entity.get_by_id() should raise ResourceNotFound for non-existent ID."""
    core = Core(test_db, atomic=False)
    with pytest.raises(ResourceNotFound):
        core.entity.get_by_id("99999999-9999-9999-9999-999999999999")


# ============================================================================
# TransactionOperations integration tests via Core
# ============================================================================

def test_core_transaction_create():
    """core.transaction.create() should create transaction with automatic entity creation."""
    import tempfile
    import os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        entity_id = None
        conn1 = sqlite3.connect(db_path)
        conn1.row_factory = sqlite3.Row
        conn1.execute("PRAGMA foreign_keys = ON")
        with Core(conn1, atomic=True) as core:
            # Create transaction - entity created automatically
            entity_id = core.transaction.create(
                amount=100.50,
                transaction_date=date.today(),
                description="Test transaction",
                account="Test Account"
            )

        # Verify transaction was created (using fresh connection)
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        row = conn2.execute("SELECT * FROM transactions WHERE id = ?", (entity_id,)).fetchone()

        assert row is not None
        assert row['amount'] == 100.50
        assert row['description'] == "Test transaction"

        # Verify entity was also created
        entity_row = conn2.execute("SELECT * FROM entity WHERE id = ?", (entity_id,)).fetchone()
        assert entity_row is not None
        assert entity_row['type'] == 'transactions'
    finally:
        os.unlink(db_path)


def test_core_transaction_get_by_id():
    """core.transaction.get_by_id() should return transaction."""
    import tempfile
    import os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        entity_id = None
        conn1 = sqlite3.connect(db_path)
        conn1.row_factory = sqlite3.Row
        conn1.execute("PRAGMA foreign_keys = ON")
        with Core(conn1, atomic=True) as core:
            # Create transaction - entity created automatically
            entity_id = core.transaction.create(
                amount=50.00,
                transaction_date=date.today(),
                description="Test",
                account="Account"
            )

        # Get transaction with fresh connection
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        core2 = Core(conn2, atomic=False)
        row = core2.transaction.get_by_id(entity_id)

        assert row is not None
        assert row['amount'] == 50.00
    finally:
        os.unlink(db_path)


def test_core_transaction_get_by_id_raises_not_found(test_db):
    """core.transaction.get_by_id() should raise ResourceNotFound for non-existent ID."""
    core = Core(test_db, atomic=False)
    with pytest.raises(ResourceNotFound):
        core.transaction.get_by_id("99999999-9999-9999-9999-999999999999")


def test_core_transaction_list():
    """core.transaction.list() should return list of transactions."""
    import tempfile
    import os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "memogarden" / "schema" / "schema.sql"
        with sqlite3.connect(db_path) as init_conn:
            init_conn.row_factory = sqlite3.Row
            with open(schema_path, "r") as f:
                init_conn.executescript(f.read())
            init_conn.commit()

        # Create multiple transactions
        conn1 = sqlite3.connect(db_path)
        conn1.row_factory = sqlite3.Row
        conn1.execute("PRAGMA foreign_keys = ON")
        with Core(conn1, atomic=True) as core:
            for i in range(3):
                core.transaction.create(
                    amount=float(10 + i * 10),
                    transaction_date=date.today(),
                    description=f"Transaction {i}",
                    account="Account"
                )

        # List transactions with fresh connection
        conn2 = sqlite3.connect(db_path)
        conn2.row_factory = sqlite3.Row
        core2 = Core(conn2, atomic=False)
        rows = core2.transaction.list({})

        assert len(rows) == 3
    finally:
        os.unlink(db_path)


# ============================================================================
# Legacy Flask support tests removed
# ============================================================================
# The legacy get_db() and close_db() functions were removed in Step 16
# of the refactor plan. All code now uses the Core API pattern.
