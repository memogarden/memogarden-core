# Refactor Plan: MemoGarden Core Architecture

**Status**: In Progress - Step 6 Next (Core API)
**Created**: 2025-12-23
**Based on**: [refactor-proposal.md](./refactor-proposal.md) v1.3

---

## Overview

This refactor implements the Core-based database API, centralized utilities, and improved validation patterns documented in refactor-proposal.md. The plan is designed to be executed incrementally, with each step completed and tested in a single coding agent session.

### Refactoring Principles

1. **Test First** - Write tests for new implementation before writing implementation
2. **Preserve Functionality** - Don't delete/invalidate existing code until new code passes tests
3. **Incremental Migration** - Refactor affected code only after new implementation is validated
4. **Continuous Testing** - All tests must pass after each step
5. **Documentation Updates** - Update AGENTS.md only when new interface is ready

---

## Step 1: Create Utils Module (isodatetime, uid) ✅ COMPLETED

**Goal**: Establish centralized utilities for datetime/date and UUID operations.

**Session Scope**: Create utils/ module with comprehensive tests, no integration yet.

**Status**: ✅ Completed 2025-12-23
- Created `utils/isodatetime.py` with `to_timestamp()`, `to_datetime()`, `now()`, `to_datestring()`
- Created `utils/uid.py` with `generate_uuid()`
- Updated `utils/__init__.py` with module exports
- Created `tests/utils/test_isodatetime.py` (13 tests)
- Created `tests/utils/test_uid.py` (4 tests)
- Refactored `database.py` and `api/v1/transactions.py` to use new utils
- ✅ Updated `AGENTS.md` with utility conventions and module-level import patterns
- All 17 utils tests pass
- Full test suite (111 tests) passes

### 1.1 Create utils/isodatetime.py

**File**: `memogarden_core/utils/isodatetime.py`

**Implementation**:
```python
"""ISO 8601 datetime/date conversion utilities.

This module centralizes all transformations between Python datetime/date objects
and ISO 8601 strings. All date/time operations should use these functions
to ensure consistency and make usage clear across the codebase.
"""

from datetime import datetime, date, UTC


def to_timestamp(dt: datetime) -> str:
    """Convert datetime to ISO 8601 UTC timestamp string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat().replace("+00:00", "Z")


def to_datetime(timestamp: str) -> datetime:
    """Convert ISO 8601 UTC timestamp string to datetime."""
    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


def now() -> str:
    """Get current UTC timestamp as ISO 8601 string."""
    return to_timestamp(datetime.now(UTC))


def to_datestring(d: date) -> str:
    """Convert date to ISO 8601 date string (YYYY-MM-DD)."""
    return d.isoformat()
```

**Tests**: `tests/utils/test_isodatetime.py`
- Test `to_timestamp()` with naive datetime (treats as UTC)
- Test `to_timestamp()` with aware datetime
- Test `to_datetime()` with Z suffix
- Test `to_datetime()` with +00:00 suffix
- Test `now()` returns valid ISO 8601 format
- Test `to_datestring()` converts dates correctly
- Test round-trip conversion (datetime → timestamp → datetime)
- Test round-trip conversion (date → datestring → date)

### 1.2 Create utils/uid.py

**File**: `memogarden_core/utils/uid.py`

**Implementation**:
```python
"""UUID generation utilities.

This module centralizes all UUID generation. This is the ONLY module that
should import uuid4. All other code should use uid.generate_uuid().
"""

from uuid import uuid4


def generate_uuid() -> str:
    """Generate a random UUID v4 as a string."""
    return str(uuid4())
```

**Tests**: `tests/utils/test_uid.py`
- Test `generate_uuid()` returns valid UUID v4 format
- Test `generate_uuid()` returns unique values (multiple calls)
- Test format matches pattern: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`

### 1.3 Update utils/__init__.py

**File**: `memogarden_core/utils/__init__.py`

Make utils a proper package.

**Verification**:
- All tests pass
- No existing code broken (utils not integrated yet)

---

## Step 2: Create Schema Module with Domain Types ✅ COMPLETED

**Goal**: Establish /schema as source of truth for data model.

**Session Scope**: Create schema/ directory, domain types, move schema.sql.

**Status**: ✅ Completed 2025-12-23
- Created `schema/` directory with `__init__.py`
- Created `schema/types.py` with `Timestamp` and `Date` domain types
- Added `Date.today()` classmethod for getting current date
- Created `tests/schema/test_types.py` (18 tests total)
- Moved `db/schema.sql` → `schema/schema.sql`
- Updated `database.py` init_db() to reference new location
- Updated `tests/conftest.py` to reference new schema location
- Refactored `db/seed.py` to use `isodatetime.to_datestring()` instead of `.isoformat()`
- All 129 tests pass (18 schema tests + 111 existing)
- Domain types provide type-safe datetime/date operations
- All `.isoformat()` calls now go through centralized `isodatetime` utility

### 2.1 Create schema/ Directory Structure

```
schema/
├── __init__.py
├── types.py
└── schema.sql (moved from db/)
```

### 2.2 Create schema/types.py

**File**: `memogarden_core/schema/types.py`

**Implementation**:
```python
"""Domain types for MemoGarden.

These types define the fundamental data representations used throughout
the system, ensuring consistency between API, database, and business logic.
"""

from datetime import datetime
from ..utils import isodatetime


class Timestamp(str):
    """ISO 8601 UTC timestamp string."""

    @classmethod
    def from_datetime(cls, dt: datetime) -> 'Timestamp':
        """Convert datetime to Timestamp."""
        return cls(isodatetime.to_timestamp(dt))

    @classmethod
    def now(cls) -> 'Timestamp':
        """Get current UTC timestamp."""
        return cls(isodatetime.now())

    def to_datetime(self) -> datetime:
        """Convert Timestamp to datetime."""
        return isodatetime.to_datetime(self)


class Date(str):
    """ISO 8601 date string."""

    @classmethod
    def from_date(cls, d: date) -> 'Date':
        """Convert date to Date string."""
        return cls(isodatetime.to_datestring(d))

    @classmethod
    def today(cls) -> 'Date':
        """Get today's date as Date string."""
        return cls.from_date(date.today())

    def to_date(self) -> date:
        """Convert Date string to date object."""
        return date.fromisoformat(self)
```

**Tests**: `tests/schema/test_types.py`
- Test `Timestamp.from_datetime()` with naive/aware datetimes
- Test `Timestamp.now()` returns valid timestamp
- Test `Timestamp.to_datetime()` round-trip
- Test `Timestamp` is str subtype
- Test `Date.from_date()` conversion
- Test `Date.today()` returns today's date
- Test `Date.today()` round-trip conversion
- Test `Date.to_date()` round-trip
- Test `Date` is str subtype

### 2.3 Move schema.sql

**Move**: `db/schema.sql` → `schema/schema.sql`

**Update**: `database.py` init_db() function to reference new location:
```python
schema_path = Path(__file__).parent.parent / "schema" / "schema.sql"
```

**Tests**: Verify database initialization still works
- Run existing tests to ensure schema.sql migration doesn't break init_db()

**Verification**:
- All 129 tests pass
- schema.sql successfully moved and referenced
- Domain types tested in isolation
- `Date.today()` method added and tested
- `db/seed.py` refactored to use `isodatetime.to_datestring()`
- All `.isoformat()` calls in production code go through `isodatetime` utility

---

## Step 3: Create db/query.py Module ✅ COMPLETED

**Goal**: Extract query builders for patterns repeated >2 times.

**Session Scope**: Create query.py with comprehensive unit tests.

**Status**: ✅ Completed 2025-12-23
- Created `db/query.py` with `build_where_clause()` and `build_update_clause()`
- Created `tests/db/test_query.py` with 29 comprehensive tests
- Tests cover: empty dicts, None values, param_map, exclude sets, type preservation, order preservation
- SQL injection safety tests confirm parameterized query behavior
- All 158 tests pass (29 new + 129 existing)
- Query builders ready for integration in Step 5

### 3.1 Create db/query.py

**File**: `memogarden_core/db/query.py`

**Implementation**:
```python
"""Query builders and utilities.

QUERY BUILDER SCOPE:
Abstract query patterns that are repeated MORE THAN TWICE.
Don't build a full ORM - just helpers for common patterns.
"""

from typing import Any


def build_where_clause(
    conditions: dict[str, Any],
    param_map: dict[str, str] | None = None
) -> tuple[str, list[Any]]:
    """Build dynamic WHERE clause from condition dictionary."""
    where_parts = []
    params = []

    for key, value in conditions.items():
        if value is None:
            continue

        if param_map and key in param_map:
            where_parts.append(param_map[key])
            params.append(value)
        else:
            where_parts.append(f"{key} = ?")
            params.append(value)

    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    return where_clause, params


def build_update_clause(
    data: dict[str, Any],
    exclude: set[str] | None = None
) -> tuple[str, list[Any]]:
    """Build dynamic UPDATE clause from data dictionary."""
    exclude = exclude or set()
    update_parts = []
    params = []

    for key, value in data.items():
        if value is None or key in exclude:
            continue
        update_parts.append(f"{key} = ?")
        params.append(value)

    update_clause = ", ".join(update_parts)
    return update_clause, params
```

**Tests**: `tests/db/test_query.py`
- Test `build_where_clause()` with empty dict
- Test `build_where_clause()` with None values (excluded)
- Test `build_where_clause()` with param_map
- Test `build_where_clause()` without param_map
- Test `build_update_clause()` with empty dict
- Test `build_update_clause()` with exclude set
- Test `build_update_clause()` with None values (excluded)
- Test SQL injection safety (parameterized queries)

---

## Step 4: Create db/entity.py with EntityOperations Class ✅ COMPLETED

**Goal**: Implement entity registry operations using new utils.

**Session Scope**: Create EntityOperations class, test with real database.

**Status**: ✅ Completed 2025-12-23
- Created `db/entity.py` with `EntityOperations` class
- Methods: `create()`, `get_by_id()`, `supersede()`, `update_timestamp()`
- Created `tests/db/test_entity.py` with 15 behavior-focused tests
- All 173 tests pass (15 new + 158 existing)
- No mocks used - tests use in-memory SQLite and verify observable behavior
- Updated `AGENTS.md` with testing philosophy (no mocks, behavior-focused testing)
- Uses centralized utils (`isodatetime.now()`, `uid.generate_uuid()`)

**Architecture Decision: Composition Over Inheritance**

TransactionOperations and EntityOperations use **composition**, not inheritance:
- Each operations class is focused and type-safe
- TransactionOperations can delegate to EntityOperations via `core.entity`
- No inheritance hierarchy - Core owns each operations class as separate properties
- This matches the domain model: transactions *have an* entity registry entry

```python
# Composition pattern used in Core
class Core:
    @property
    def entity(self) -> EntityOperations: ...

    @property
    def transaction(self) -> TransactionOperations: ...

# TransactionOperations delegates when needed
def transaction_delete(uuid: str):
    core.entity.supersede(uuid, tombstone_id)  # Delegates to entity ops
```

### 4.1 Create db/entity.py

**File**: `memogarden_core/db/entity.py`

**Implementation**:
```python
"""Entity registry operations.

The entity registry provides a global table tracking all entities
in the system.

IMPORT CONVENTION:
- Core accesses these through core.entity property
- NO direct import needed when using Core API
"""

import sqlite3
from ..utils import uid, isodatetime
from ..exceptions import ResourceNotFound


class EntityOperations:
    """Entity registry operations.

    Provides methods for creating, retrieving, and managing entities
    in the global entity registry.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize entity operations with a database connection.

        Args:
            conn: SQLite connection with row_factory set to sqlite3.Row
        """
        self._conn = conn

    def create(
        self,
        entity_type: str,
        entity_id: str | None = None,
        group_id: str | None = None,
        derived_from: str | None = None
    ) -> str:
        """Create entity in global registry.

        Args:
            entity_type: The type of entity (e.g., 'transactions', 'recurrences')
            entity_id: Optional UUID. If not provided, generates a new UUID.
            group_id: Optional group ID for clustering related entities
            derived_from: Optional ID of source entity for provenance tracking

        Returns:
            The entity ID (generated or provided)
        """
        if entity_id is None:
            entity_id = uid.generate_uuid()

        now = isodatetime.now()

        self._conn.execute(
            """INSERT INTO entity (id, type, group_id, derived_from, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (entity_id, entity_type, group_id, derived_from, now, now)
        )

        return entity_id

    def get_by_id(
        self,
        entity_id: str,
        table_or_view: str = "entity",
        entity_type: str = "Entity"
    ) -> sqlite3.Row:
        """Get entity by ID, raise ResourceNotFound if not found.

        Args:
            entity_id: The UUID of the entity
            table_or_view: Table or view name to query (default: 'entity')
            entity_type: Human-readable type name for error messages

        Returns:
            sqlite3.Row with entity data

        Raises:
            ResourceNotFound: If entity_id doesn't exist
        """
        row = self._conn.execute(
            f"SELECT * FROM {table_or_view} WHERE id = ?",
            (entity_id,)
        ).fetchone()

        if not row:
            raise ResourceNotFound(
                f"{entity_type} '{entity_id}' not found",
                {"entity_id": entity_id}
            )

        return row

    def supersede(self, old_id: str, new_id: str) -> None:
        """Mark entity as superseded by another entity.

        Args:
            old_id: The ID of the entity being superseded
            new_id: The ID of the superseding entity

        Note:
            Both entities should exist before calling this method.
            The old entity will have superseded_by and superseded_at set.
        """
        now = isodatetime.now()

        self._conn.execute(
            """UPDATE entity
               SET superseded_by = ?, superseded_at = ?, updated_at = ?
               WHERE id = ?""",
            (new_id, now, now, old_id)
        )

    def update_timestamp(self, entity_id: str) -> None:
        """Update the updated_at timestamp for an entity.

        Args:
            entity_id: The ID of the entity to update
        """
        now = isodatetime.now()

        self._conn.execute(
            "UPDATE entity SET updated_at = ? WHERE id = ?",
            (now, entity_id)
        )
```

**Tests**: `tests/db/test_entity.py`
- Test `create()` generates UUID if not provided
- Test `create()` uses provided UUID
- Test `create()` inserts correct values in entity table
- Test `get_by_id()` returns row for existing entity
- Test `get_by_id()` raises ResourceNotFound for non-existent entity
- Test `supersede()` updates superseded_by and superseded_at
- Test `update_timestamp()` updates updated_at field
- Test all operations use utils (isodatetime.now, uid.generate_uuid)

**Verification**:
- All EntityOperations tests pass
- Uses in-memory SQLite for tests
- EntityOperations not integrated with Core yet

---

## Step 5: Create db/transaction.py with TransactionOperations Class ✅ COMPLETED

**Goal**: Implement transaction operations using query builders.

**Session Scope**: Create TransactionOperations class with tests.

**Status**: ✅ Completed 2025-12-23
- Created `db/transaction.py` with `TransactionOperations` class
- Methods: `get_by_id()`, `create()`, `list()`, `update()`
- Created `tests/db/test_transaction.py` with 23 comprehensive tests
- All 196 tests pass (23 new + 173 existing)
- Uses query builders from `db/query.py`
- Uses centralized utils (`isodatetime.to_datestring()`)
- Handles `include_superseded` flag with special-case SQL fragment

**Note**: TransactionOperations uses composition - it delegates to EntityOperations
via `core.entity` when needed (e.g., for supersede operations). It does NOT inherit
from EntityOperations to avoid LSP violations and keep each class focused.

### 5.1 Create db/transaction.py

**File**: `memogarden_core/db/transaction.py`

**Implementation**:
```python
"""Transaction-specific operations.

IMPORT CONVENTION:
- Core accesses these through core.transaction property
- Delegates to core.entity for registry-level operations
"""

import sqlite3
from datetime import date
from typing import Any
from . import query
from ..utils import isodatetime
from ..exceptions import ResourceNotFound


class TransactionOperations:
    """Transaction operations.

    Uses composition with EntityOperations - delegates registry-level
    operations through core.entity when needed.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_by_id(self, transaction_id: str) -> sqlite3.Row:
        """Get transaction by ID."""
        row = self._conn.execute(
            "SELECT * FROM transactions_view WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        if not row:
            raise ResourceNotFound(
                f"Transaction '{transaction_id}' not found",
                {"transaction_id": transaction_id}
            )

        return row

    def create(
        self,
        transaction_id: str,
        amount: float,
        transaction_date: date,
        description: str,
        account: str,
        category: str | None = None,
        notes: str | None = None,
        author: str = "system"
    ) -> None:
        """Create a transaction."""
        date_str = transaction_date.isoformat()

        self._conn.execute(
            """INSERT INTO transactions
               (id, amount, currency, transaction_date, description, account, category, author, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (transaction_id, amount, "SGD", date_str, description, account, category, author, notes)
        )

    def list(
        self,
        filters: dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> list[sqlite3.Row]:
        """List transactions with filtering."""
        param_map = {
            "start_date": "t.transaction_date >= ?",
            "end_date": "t.transaction_date <= ?",
            "account": "t.account = ?",
            "category": "t.category = ?",
        }

        conditions = {k: v for k, v in filters.items() if v is not None}

        if not filters.get("include_superseded"):
            conditions["superseded_by"] = None
            param_map["superseded_by"] = "e.superseded_by IS NULL"

        where_clause, params = query.build_where_clause(conditions, param_map)
        params.extend([limit, offset])

        query_sql = f"""
            SELECT t.*,
                   e.created_at, e.updated_at, e.superseded_by, e.superseded_at,
                   e.group_id, e.derived_from
            FROM transactions t
            JOIN entity e ON t.id = e.id
            WHERE {where_clause}
            ORDER BY t.transaction_date DESC, e.created_at DESC
            LIMIT ? OFFSET ?
        """

        return self._conn.execute(query_sql, params).fetchall()

    def update(self, transaction_id: str, data: dict[str, Any]) -> None:
        """Update transaction with partial data."""
        # Convert date to string if present
        if "transaction_date" in data and data["transaction_date"] is not None:
            data["transaction_date"] = data["transaction_date"].isoformat()

        # Build UPDATE clause
        update_clause, params = query.build_update_clause(
            data,
            exclude={"id"}
        )

        if update_clause:
            params.append(transaction_id)

            # Update transaction
            self._conn.execute(
                f"UPDATE transactions SET {update_clause} WHERE id = ?",
                params
            )

            # Update entity registry timestamp
            # Note: Could delegate to core.entity.update_timestamp() after Core integration
            now = isodatetime.now()
            self._conn.execute(
                "UPDATE entity SET updated_at = ? WHERE id = ?",
                (now, transaction_id)
            )
```

**Tests**: `tests/db/test_transaction.py`
- Test `get_by_id()` returns transaction for existing ID
- Test `get_by_id()` raises ResourceNotFound for non-existent ID
- Test `create()` inserts transaction with correct values
- Test `list()` returns all transactions (no filters)
- Test `list()` filters by account
- Test `list()` filters by date range
- Test `list()` excludes superseded by default
- Test `list()` includes superseded when flag set
- Test `update()` updates only provided fields
- Test `update()` handles None values correctly
- Test `update()` updates entity.updated_at

**Verification**:
- All TransactionOperations tests pass
- Query builders tested in integration context
- TransactionOperations not integrated with Core yet

---

## Step 6: Create db/__init__.py with Core API

**Goal**: Implement Core-based database API with connection management.

**Session Scope**: Create Core class and get_core() function, integrate EntityOperations and TransactionOperations.

### 6.1 Create db/__init__.py

**File**: `memogarden_core/db/__init__.py`

**Implementation**:
```python
"""Database module for MemoGarden Core.

This module provides the Core API for database operations.
Core encapsulates connection management and provides access to entity operations.

ARCHITECTURE:
- Core owns its connection (no Flask g.db dependency)
- Connection closes on context exit (atomic=True) or after operation (atomic=False)
- Each entity type gets an encapsulated class with related operations
"""

from contextvars import ContextVar
from pathlib import Path
from typing import Generator
import sqlite3
from .config import settings

# Thread-local storage for atomic Core
_core_context: ContextVar["Core"] = ContextVar("_core_context", default=None)


class Core:
    """
    Database Core with entity operations.

    Maintains its own connection and transaction state.
    Provides access to entity operations through properties.

    Connection Lifecycle:
    - atomic=True: Connection closes on __exit__ from context manager
    - atomic=False: Connection closes after each operation (autocommit)
    """

    def __init__(self, connection: sqlite3.Connection, atomic: bool = False):
        self._conn = connection
        self._atomic = atomic
        self._entity_ops = None
        self._transaction_ops = None

    @property
    def entity(self) -> "EntityOperations":
        """Entity registry operations."""
        if self._entity_ops is None:
            from .entity import EntityOperations
            self._entity_ops = EntityOperations(self._conn)
        return self._entity_ops

    @property
    def transaction(self) -> "TransactionOperations":
        """Transaction operations."""
        if self._transaction_ops is None:
            from .transaction import TransactionOperations
            self._transaction_ops = TransactionOperations(self._conn)
        return self._transaction_ops

    def __enter__(self) -> "Core":
        if not self._atomic:
            raise RuntimeError(
                "Core must be created with atomic=True for context manager use. "
                "Use: with db.get_core(atomic=True) as core:"
            )
        _core_context.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            _core_context.set(None)
            self._conn.close()

    def __del__(self):
        """Cleanup connection if not already closed."""
        if hasattr(self, "_conn") and self._conn:
            try:
                self._conn.close()
            except:
                pass  # Ignore errors during garbage collection


def _create_connection() -> sqlite3.Connection:
    """Create a fresh database connection."""
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_core(atomic: bool = False) -> Core:
    """
    Get a database Core instance.

    Args:
        atomic: If True, returns a Core that MUST be used as context manager.
                Use for multi-operation transactions.
                If False (default), returns a Core with autocommit semantics.

    Returns:
        Core instance with entity/transaction operations
    """
    conn = _create_connection()
    return Core(conn, atomic=atomic)


# Legacy Flask support (kept during migration)
def get_db() -> sqlite3.Connection:
    """
    Legacy Flask request-scoped connection.

    DEPRECATED: Use get_core() instead.
    """
    from flask import g
    if 'db' not in g:
        g.db = _create_connection()
    return g.db


def close_db(e=None):
    """Legacy Flask connection cleanup. DEPRECATED."""
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database by running schema.sql if not already initialized."""
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as db:
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_metadata'"
        )
        if cursor.fetchone():
            return

        schema_path = Path(__file__).parent.parent / "schema" / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            db.executescript(schema_sql)
            db.commit()
```

**Tests**: `tests/db/test_core.py`
- Test `get_core(atomic=False)` returns Core instance
- Test `get_core(atomic=True)` returns Core instance
- Test Core.entity property returns EntityOperations
- Test Core.transaction property returns TransactionOperations
- Test `with get_core(atomic=True)` context manager
- Test context manager commits on success
- Test context manager rolls back on exception
- Test context manager closes connection on exit
- Test RuntimeError when atomic=True without context manager
- Test autocommit mode closes connection after operation
- Test legacy get_db() still works

**Verification**:
- All Core API tests pass
- EntityOperations and TransactionOperations integrated
- Legacy get_db() still functional (not removed yet)

---

## Step 7: Migrate Route Handler to Use Core API

**Goal**: Update one route handler to use new Core API as proof of concept.

**Session Scope**: Migrate POST /transactions endpoint to Core API.

### 7.1 Update POST /transactions Handler

**File**: `memogarden_core/api/v1/transactions.py`

**Before** (keep as comment for reference):
```python
@transactions_bp.route("", methods=["POST"])
def create_transaction():
    try:
        data = TransactionCreate(**request.get_json())
    except ValidationError as e:
        raise MGValidationError("Invalid request data", {"errors": e.errors()})

    uuid = str(uuid4())
    entity_id = create_entity(get_db(), "transactions", uuid)

    now = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

    get_db().execute(
        """INSERT INTO transactions
           (id, amount, currency, transaction_date, description, account, category, author, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (uuid, data.amount, "SGD", data.transaction_date.isoformat(),
         data.description, data.account, data.category, "system", data.notes)
    )
    get_db().commit()

    # ... response building ...
```

**After**:
```python
from db import get_core

@transactions_bp.post("")
def create_transaction():
    """Create a new transaction."""
    try:
        data = TransactionCreate(**request.get_json())
    except ValidationError as e:
        raise MGValidationError("Invalid request data", {"errors": e.errors()})

    with get_core(atomic=True) as core:
        uuid = core.entity.create("transactions")
        core.transaction.create(
            uuid,
            amount=data.amount,
            transaction_date=data.transaction_date,
            description=data.description,
            account=data.account,
            category=data.category,
            notes=data.notes
        )

    # ... response building (unchanged) ...
```

**Tests**: Update existing tests in `tests/api/test_transactions.py`
- Test POST /transactions still works
- Test transaction created in database
- Test entity registry entry created
- Test rollback on error (verify atomic behavior)

**Verification**:
- All existing tests pass
- New Core API path tested
- Old code kept as comment for reference

---

## Step 8: Create api/validation.py with @validate_request Decorator

**Goal**: Implement type-annotation-based validation decorator.

**Session Scope**: Create validation.py with comprehensive tests.

### 8.1 Create api/validation.py

**File**: `memogarden_core/api/validation.py`

**Implementation**:
```python
"""Request validation decorators.

VALIDATION MESSAGE PRINCIPLE:
Assume API is used by human/agent stakeholders. Provide clear, detailed
validation error messages. No need to obscure information for "security".
"""

import inspect
import functools
from flask import request
from pydantic import BaseModel, ValidationError
from ..exceptions import ValidationError as MGValidationError


def validate_request(f):
    """
    Decorator that validates request JSON against the view function's
    first parameter type annotation.

    Handles path parameters separately from request body.
    """
    # Get type annotation for first parameter
    sig = inspect.signature(f)
    params = list(sig.parameters.values())

    if not params:
        raise TypeError(
            f"Function {f.__name__} has no parameters to validate. "
            "The first parameter should have a Pydantic model type annotation."
        )

    first_param = params[0]
    model_class = first_param.annotation

    if model_class is inspect.Parameter.empty:
        raise TypeError(
            f"Function {f.__name__}'s first parameter '{first_param.name}' "
            "lacks a type annotation. Expected a Pydantic BaseModel subclass."
        )

    if not (isinstance(model_class, type) and issubclass(model_class, BaseModel)):
        raise TypeError(
            f"Type annotation for '{first_param.name}' must be a Pydantic BaseModel subclass, "
            f"got {model_class!r}"
        )

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # Check if first param is a path parameter (in view_args)
        if first_param.name in request.view_args:
            # Path parameter - pass through as string
            path_value = request.view_args[first_param.name]
            return f(path_value, *args, **kwargs)

        # Body parameter - validate against Pydantic model
        if request.json is None:
            raise MGValidationError(
                "Request body is required but was not provided.",
                {
                    "expected": model_class.__name__,
                    "received": None,
                    "schema": model_class.model_json_schema()
                }
            )

        try:
            validated_data = model_class(**request.json)
        except ValidationError as e:
            # Provide detailed, helpful error messages
            errors = e.errors()
            error_details = []

            for error in errors:
                loc = " -> ".join(str(l) for l in error["loc"])
                error_details.append({
                    "field": loc,
                    "message": error["msg"],
                    "expected_type": error["type"],
                })

            raise MGValidationError(
                f"Request validation failed for {model_class.__name__}. "
                f"See details for specific fields.",
                {
                    "model": model_class.__name__,
                    "errors": error_details,
                    "received": request.json,
                }
            )

        # Inject validated data as first parameter
        return f(validated_data, *args, **kwargs)

    return wrapper
```

**Tests**: `tests/api/test_validation.py`
- Test validates valid request body
- Test raises MGValidationError for invalid body
- Test error details include field, message, expected_type
- Test passes through path parameters unchanged
- Test raises clear error when body is None
- Test raises TypeError when function has no parameters
- Test raises TypeError when first parameter lacks annotation
- Test raises TypeError when annotation is not BaseModel

**Verification**:
- All validation tests pass
- Decorator not integrated yet

---

## Step 9: Apply @validate_request to POST /transactions

**Goal**: Apply validation decorator to migrated route handler.

**Session Scope**: Integrate @validate_request with POST /transactions.

### 9.1 Update POST /transactions Handler

**File**: `memogarden_core/api/v1/transactions.py`

**Before**:
```python
@transactions_bp.post("")
def create_transaction():
    """Create a new transaction."""
    try:
        data = TransactionCreate(**request.get_json())
    except ValidationError as e:
        raise MGValidationError("Invalid request data", {"errors": e.errors()})

    with get_core(atomic=True) as core:
        # ... rest of implementation
```

**After**:
```python
from api.validation import validate_request

@transactions_bp.post("")
@validate_request
def create_transaction(data: TransactionCreate):
    """Create a new transaction."""
    with get_core(atomic=True) as core:
        uuid = core.entity.create("transactions")
        core.transaction.create(
            uuid,
            amount=data.amount,
            transaction_date=data.transaction_date,
            description=data.description,
            account=data.account,
            category=data.category,
            notes=data.notes
        )

    # ... response building ...
```

**Tests**: Update `tests/api/test_transactions.py`
- Test valid request creates transaction
- Test invalid request body returns detailed validation errors
- Test validation error includes field path
- Test validation error includes expected type
- Test missing required field returns clear error
- Test wrong type returns clear error

**Verification**:
- All tests pass
- Validation decorator applied successfully
- Manual try-except removed

---

## Step 10: Migrate GET /transactions/<uuid> to Core API

**Goal**: Migrate GET single transaction endpoint.

**Session Scope**: Update GET /transactions/<uuid> to use Core API.

### 10.1 Update GET /transactions/<uuid> Handler

**File**: `memogarden_core/api/v1/transactions.py`

**Before**:
```python
@transactions_bp.route("/<uuid>", methods=["GET"])
def get_transaction(uuid):
    db = get_db()

    row = db.execute(
        "SELECT * FROM transactions_view WHERE id = ?",
        (uuid,)
    ).fetchone()

    if not row:
        raise ResourceNotFound(
            "Transaction not found",
            {"transaction_id": uuid}
        )

    # ... response building ...
```

**After**:
```python
@transactions_bp.get("/<uuid>")
def get_transaction(uuid: str):
    """Get a transaction by ID."""
    core = get_core()
    row = core.transaction.get_by_id(uuid)

    # ... response building (unchanged) ...
```

**Tests**: Update `tests/api/test_transactions.py`
- Test GET existing transaction returns 200
- Test GET non-existent transaction raises ResourceNotFound

**Verification**:
- All tests pass
- Core API used for single transaction fetch
- Error handling moved to TransactionOperations

---

## Step 11: Migrate GET /transactions (list) to Core API

**Goal**: Migrate list transactions endpoint.

**Session Scope**: Update GET /transactions to use Core API.

### 11.1 Update GET /transactions Handler

**File**: `memogarden_core/api/v1/transactions.py`

**Before**:
```python
@transactions_bp.route("", methods=["GET"])
def list_transactions():
    db = get_db()

    # ... build query manually ...
    rows = db.execute(query_sql, params).fetchall()

    # ... response building ...
```

**After**:
```python
@transactions_bp.get("")
def list_transactions():
    """List transactions with optional filtering."""
    # Extract query parameters
    account = request.args.get("account")
    category = request.args.get("category")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    include_superseded = request.args.get("include_superseded", "false").lower() == "true"

    filters = {
        "account": account,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "include_superseded": include_superseded
    }

    core = get_core()
    rows = core.transaction.list(filters)

    # ... response building (unchanged) ...
```

**Tests**: Update `tests/api/test_transactions.py`
- Test GET /transactions returns all transactions
- Test filter by account works
- Test filter by category works
- Test filter by date range works
- Test include_superseded flag works

**Verification**:
- All tests pass
- Query builder tested in integration
- List operations centralized in TransactionOperations

---

## Step 12: Migrate PUT /transactions/<uuid> to Core API

**Goal**: Migrate update transaction endpoint with validation and query builder.

**Session Scope**: Update PUT endpoint with @validate_request and Core API.

### 12.1 Update PUT /transactions/<uuid> Handler

**File**: `memogarden_core/api/v1/transactions.py`

**Before**:
```python
@transactions_bp.route("/<uuid>", methods=["PUT"])
def update_transaction(uuid):
    try:
        data = TransactionUpdate(**request.get_json())
    except ValidationError as e:
        raise MGValidationError("Invalid request data", {"errors": e.errors()})

    # ... manual update logic ...
```

**After**:
```python
@transactions_bp.put("/<uuid>")
@validate_request
def update_transaction(uuid: str, data: TransactionUpdate):
    """Update a transaction (partial update)."""
    core = get_core()

    # Verify transaction exists
    core.transaction.get_by_id(uuid)

    # Build update data from only provided fields
    update_data = data.model_dump(exclude_unset=True)

    if update_data:
        core.transaction.update(uuid, update_data)

    # ... response building ...
```

**Tests**: Update `tests/api/test_transactions.py`
- Test PUT with valid partial update
- Test PUT with no fields returns successfully
- Test PUT updates only provided fields
- Test PUT non-existent transaction raises error

**Verification**:
- All tests pass
- Query builder integration tested
- Partial update pattern validated

---

## Step 13: Migrate DELETE /transactions/<uuid> to Core API

**Goal**: Migrate delete transaction endpoint.

**Session Scope**: Update DELETE endpoint to use Core API.

### 13.1 Update DELETE /transactions/<uuid> Handler

**File**: `memogarden_core/api/v1/transactions.py`

**Before**:
```python
@transactions_bp.route("/<uuid>", methods=["DELETE"])
def delete_transaction(uuid):
    db = get_db()

    # Check existence
    row = db.execute(
        "SELECT * FROM transactions_view WHERE id = ?",
        (uuid,)
    ).fetchone()

    if not row:
        raise ResourceNotFound("Transaction not found", {"transaction_id": uuid})

    # Soft delete via superseding
    # ... manual implementation ...
```

**After**:
```python
@transactions_bp.delete("/<uuid>")
def delete_transaction(uuid: str):
    """Delete a transaction (soft delete via superseding)."""
    with get_core(atomic=True) as core:
        # Verify transaction exists
        core.transaction.get_by_id(uuid)

        # Create tombstone entity
        tombstone_id = core.entity.create("transactions")

        # Mark original as superseded
        core.entity.supersede(uuid, tombstone_id)

    return "", 204
```

**Tests**: Update `tests/api/test_transactions.py`
- Test DELETE existing transaction returns 204
- Test DELETE non-existent transaction raises error
- Test deleted transaction marked as superseded
- Test tombstone entity created

**Verification**:
- All tests pass
- Atomic transaction pattern validated
- Soft delete via superseding implemented

---

## Step 14: Update Route Syntax to Flask .get(), .post(), etc.

**Goal**: Standardize route declaration style across all endpoints.

**Session Scope**: Update all remaining route declarations.

### 14.1 Update All Route Declarations

**File**: `memogarden_core/api/v1/transactions.py`

Replace all `.route("", methods=["..."])` with method-specific decorators:

**Before**:
```python
@transactions_bp.route("/categories", methods=["GET"])
def list_categories():
    ...

@transactions_bp.route("/accounts", methods=["GET"])
def list_accounts():
    ...
```

**After**:
```python
@transactions_bp.get("/categories")
def list_categories():
    ...

@transactions_bp.get("/accounts")
def list_accounts():
    ...
```

**Tests**: No logic changes, existing tests should pass

**Verification**:
- All tests pass
- All routes use new syntax
- Code is more readable

---

## Step 15: Move schemas to api/v1/schemas/

**Goal**: Co-locate Pydantic schemas with API version they serve.

**Session Scope**: Move schemas/ directory and update imports.

### 15.1 Move schemas Directory

**Move**:
- `memogarden_core/schemas/` → `memogarden_core/api/v1/schemas/`

### 15.2 Update Imports

**Files to update**:
- `memogarden_core/api/v1/transactions.py`
- `tests/api/test_transactions.py`
- Any other files importing schemas

**Before**:
```python
from schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
```

**After**:
```python
from api.v1.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
```

**Tests**: Update imports in test files, verify all tests pass

**Verification**:
- All tests pass
- Schemas co-located with API version
- Imports updated throughout codebase

---

## Step 16: Remove Dead Code and Legacy Functions

**Goal**: Clean up deprecated code after successful migration.

**Session Scope**: Remove legacy functions, update documentation.

### 16.1 Remove Legacy Database Functions

**File**: `memogarden_core/db/__init__.py`

**Remove**:
- `get_db()` function
- `close_db()` function

**Note**: Only remove after verifying no code uses these functions.

### 16.2 Remove Old Helper Functions

**File**: `memogarden_core/database.py` (or delete entirely)

**Remove**:
- `create_entity()` function
- `supersede_entity()` function
- `get_entity_type()` function
- Any other duplicated code

### 16.3 Remove Manual Validation Blocks

All manual `try-except ValidationError` blocks should already be replaced with `@validate_request`.

**Tests**: Full test suite

**Verification**:
- All tests pass
- No dead code remaining
- Core API is sole database interface

---

## Step 17: Update AGENTS.md with New Conventions

**Goal**: Document new patterns for AI agents.

**Session Scope**: Update AGENTS.md with Core API and utility conventions.

### 17.1 Add New Sections to AGENTS.md

**File**: `/home/kureshii/memogarden/AGENTS.md`

**Add sections**:

#### Database Operations
```markdown
## Database Operations

### Core API Pattern

MemoGarden Core uses a Core-based database API for all database operations.

**Simple Query (Autocommit)**:
\`\`\`python
from db import get_core

core = get_core()
transaction = core.transaction.get_by_id(uuid)
# Connection closes automatically
\`\`\`

**Atomic Transaction (Multi-Operation)**:
\`\`\`python
from db import get_core

with get_core(atomic=True) as core:
    new_id = core.entity.create("transactions")
    core.transaction.create(new_id, amount=100, ...)
    core.entity.supersede(old_id, new_id)
    # All commit together on __exit__, or all rollback on error
\`\`\`

**Connection Lifecycle**:
- `atomic=False`: Connection closes after each operation (autocommit)
- `atomic=True`: Connection MUST be used with context manager
- RuntimeError raised if `atomic=True` used without `with`

**Entity Operations** (via `core.entity`):
- `create(entity_type, entity_id=None)` → returns UUID
- `get_by_id(entity_id, table_or_view, entity_type)` → returns row or raises ResourceNotFound
- `supersede(old_id, new_id)` → marks entity as superseded

**Transaction Operations** (via `core.transaction`):
- `get_by_id(transaction_id)` → fetch transaction
- `create(transaction_id, amount, transaction_date, ...)` → create transaction
- `list(filters, limit, offset)` → list with filtering
- `update(transaction_id, data)` → partial update

### Module-Level Import Convention

For first-party modules (`db.*`, `utils.*`, etc.), use module-level import:

\`\`\`python
# ✅ PREFERRED
from utils import isodatetime
timestamp = isodatetime.now()

from db import get_core
core = get_core()

# ❌ AVOID
from utils.isotime import now
from db.get_core import get_core
\`\`\`

Access through module namespace for clarity.
```

#### Utility Functions
```markdown
## Utility Functions

### Datetime/Timestamp Operations (utils/isodatetime.py)

All timestamp operations MUST use centralized utilities:

\`\`\`python
from utils import isodatetime

# Get current timestamp
timestamp = isodatetime.now()  # '2025-12-23T10:30:00Z'

# Convert datetime to timestamp
ts = isodatetime.to_timestamp(datetime.now(UTC))

# Convert timestamp to datetime
dt = isodatetime.to_datetime('2025-12-23T10:30:00Z')
\`\`\`

**DO NOT**:
- Import uuid4 directly (use utils.uid.generate_uuid())
- Manual datetime formatting (use utils.isodatetime functions)
- Scatter timestamp logic throughout code

### UUID Generation (utils/uid.py)

All UUID generation MUST use centralized utility:

\`\`\`python
from utils import uid

entity_id = uid.generate_uuid()
\`\`\`

This is the ONLY module that should import uuid4.
```

#### Validation
```markdown
## Request Validation

### @validate_request Decorator

All API endpoints with request bodies MUST use the `@validate_request` decorator:

\`\`\`python
from api.validation import validate_request
from api.v1.schemas.transaction import TransactionCreate

@transactions_bp.post("")
@validate_request
def create_transaction(data: TransactionCreate):
    # data is already validated TransactionCreate instance
    with get_core(atomic=True) as core:
        uuid = core.entity.create("transactions")
        core.transaction.create(uuid, ...)
    # ...
\`\`\`

**Path Parameters**:
- Path parameters (e.g., `<uuid>`) are passed as strings
- Decorator distinguishes path from body parameters automatically

\`\`\`python
@transactions_bp.put("/<uuid>")
@validate_request
def update_transaction(uuid: str, data: TransactionUpdate):
    # uuid from path (string), data from body (validated)
    # ...
\`\`\`

**DO NOT**:
- Use manual try-except ValidationError blocks
- Access request.json directly in route handlers
- Bypass the decorator for validation
```

### 17.2 Update Existing Sections

**Update "How NOT to Use SQLAlchemy"**:
- Mention Core API as the database interface
- Note that query builders exist in `db/query.py`

**Update "Common Tasks"**:
- Replace database examples with Core API examples
- Update validation examples with `@validate_request`

**Tests**: No tests, documentation update

**Verification**:
- AGENTS.md accurately reflects new patterns
- All conventions documented
- Examples provided for each pattern

---

## Step 18: Final Testing and Documentation Review

**Goal**: Complete verification that refactor is successful.

**Session Scope**: Full test suite, documentation review.

### 18.1 Run Full Test Suite

```bash
cd /home/kureshii/memogarden/memogarden-core
poetry run pytest --cov=memogarden_core
```

**Verify**:
- All tests pass
- Coverage report shows good coverage
- No unexpected failures

### 18.2 Manual API Testing

```bash
# Start dev server
poetry run flask --app memogarden_core.main run --debug
```

**Test endpoints**:
- POST /transactions - create transaction
- GET /transactions - list with filters
- GET /transactions/<uuid> - get single
- PUT /transactions/<uuid> - update
- DELETE /transactions/<uuid> - delete

### 18.3 Review Documentation

**Check**:
- AGENTS.md reflects new patterns
- refactor-plan.md is complete
- README.md still accurate
- Code docstrings accurate

### 18.4 Remove refactor-proposal.md

```bash
rm /home/kureshii/memogarden/memogarden-core/docs/refactor-proposal.md
```

**Archive** (optional): Move to docs/archive/ if desired for reference.

### 18.5 Git Commit

```bash
git add -A
git commit -m "Complete refactor: Core API, utils, validation

- Implemented Core-based database API with atomic transactions
- Centralized datetime/UUID operations in utils/
- Created @validate_request decorator for type-annotation validation
- Migrated all endpoints to use Core API
- Moved schemas to api/v1/schemas/
- Updated AGENTS.md with new conventions

All tests pass. Migration complete."
```

**Verification**:
- Full test suite passes
- Manual testing successful
- Documentation updated
- refactor-proposal.md removed
- Clean git commit

---

## Summary

This refactor plan breaks down the architecture changes into 18 discrete steps, each completable in a single coding agent session. The plan follows these principles:

1. **Test First** - New modules have tests before integration
2. **Preserve Functionality** - Old code kept until new code validated
3. **Incremental Migration** - Each step builds on previous, tested foundation
4. **Continuous Testing** - All tests pass after each step
5. **Documentation Updates** - AGENTS.md updated at end when interface ready

**Estimated Timeline**: 18 sessions (one per step)

**Entry Criteria**: Current codebase tests passing

**Exit Criteria**: All tests passing, refactor-proposal.md removed, AGENTS.md updated with new conventions

---

**Last Updated**: 2025-12-23
**Status**: Ready for Implementation
