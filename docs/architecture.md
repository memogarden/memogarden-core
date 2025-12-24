# MemoGarden Core Architecture

This document describes the key architectural decisions and design patterns used in MemoGarden Core.

## Core API Design

### Composition Over Inheritance

The database layer uses a **composition pattern**, not inheritance:

```python
class Core:
    @property
    def entity(self) -> EntityOperations: ...

    @property
    def transaction(self) -> TransactionOperations: ...
```

**Rationale:**
- Each operations class is focused and type-safe
- TransactionOperations can delegate to EntityOperations via `core.entity`
- No inheritance hierarchy - Core owns each operations class as separate properties
- Matches the domain model: transactions *have an* entity registry entry

### Connection Lifecycle

The Core API manages database connections with two modes:

**Autocommit Mode** (`atomic=False`, default):
```python
core = get_core()
transaction = core.transaction.get_by_id(uuid)
# Connection closes automatically via __del__
```

**Atomic Mode** (`atomic=True`, multi-statement transactions):
```python
with get_core(atomic=True) as core:
    new_id = core.entity.create("transactions")
    core.transaction.create(new_id, amount=100, ...)
    core.entity.supersede(old_id, new_id)
    # All commit together on __exit__, or all rollback on error
```

### Auto-Generated IDs

All entity IDs are auto-generated UUID v4 strings. This design:

1. Prevents users from accidentally passing invalid or duplicate IDs
2. Encapsulates ID generation logic within the database layer
3. Ensures UUID v4 format compliance with collision retry (3 attempts)
4. Simplifies the API - users don't need to manage ID creation

**API:**
- `EntityOperations.create(entity_type, group_id, derived_from)` → returns auto-generated UUID
- `TransactionOperations.create(amount, transaction_date, ...)` → creates entity with auto-generated ID

### Module-Level Import Convention

For first-party modules (`db.*`, `utils.*`, etc.), use **module-level imports**:

```python
# ✅ PREFERRED
from utils import isodatetime
from db import get_core
timestamp = isodatetime.now()
core = get_core()

# ❌ AVOID
from utils.isodatetime import now
from db.get_core import get_core
```

This provides clear namespace usage and better IDE navigation.

## Database Layer

### SQLite Configuration

**WAL Mode** (Write-Ahead Logging):
```python
conn.execute("PRAGMA journal_mode = WAL")
```

Enables better concurrent access by allowing readers to proceed without blocking writers.

**Foreign Keys:**
```python
conn.execute("PRAGMA foreign_keys = ON")
```

Ensures referential integrity at the database level.

### Query Builders

The `db/query.py` module provides helper functions for common SQL patterns:

- `build_where_clause(conditions, param_map)` - Dynamic WHERE clauses
- `build_update_clause(data, exclude)` - Dynamic UPDATE clauses

**Scope:** Abstract patterns repeated MORE THAN TWICE. Don't build a full ORM.

## API Layer

### Request Validation

**Validation Message Principle:**
> Assume API is used by human/agent stakeholders. Provide clear, detailed validation error messages. No need to obscure information for "security."

The `@validate_request` decorator uses type annotations to validate request bodies:

```python
@transactions_bp.post("")
@validate_request
def create_transaction(data: TransactionCreate):
    # data is already validated TransactionCreate instance
    ...
```

**Path parameters** (e.g., `<uuid>`) are automatically detected and passed as strings.

### Partial Update Pattern

For UPDATE endpoints, use Pydantic's `exclude_unset=True`:

```python
update_data = data.model_dump(exclude_unset=True)
if update_data:
    core.transaction.update(uuid, update_data)
```

This allows updating only the fields that were actually provided in the request.

## Utilities

### Centralized Operations

All datetime/UUID operations go through centralized utilities:

**`utils/isodatetime.py`:**
- `now()` - Get current UTC timestamp as ISO 8601 string
- `to_timestamp(dt)` - Convert datetime to ISO 8601 UTC timestamp
- `to_datetime(ts)` - Convert ISO 8601 timestamp to datetime
- `to_datestring(d)` - Convert date to ISO 8601 date string

**`utils/uid.py`:**
- `generate_uuid()` - Generate random UUID v4 as string (ONLY place that imports uuid4)

**Rationale:** Ensures consistency and makes usage clear across the codebase.

### Domain Types

**`schema/types.py`** provides type-safe wrappers:

- `Timestamp` - ISO 8601 UTC timestamp string (str subclass)
- `Date` - ISO 8601 date string (str subclass)

These enforce correct format at type level and provide conversion methods.

## Testing Philosophy

### No Mocks

MemoGarden tests avoid mocks, monkeypatching, and other test doubles:

**Rationale:**
- Mocks couple tests to internal implementation, making refactoring brittle
- Tests with real database (`:memory:` SQLite) provide better confidence
- Behavior-focused tests survive refactoring; implementation-focused tests break

**Guidelines:**
- Test **observable behavior**: inputs → outputs, database state, API responses
- Test **error handling**: real error conditions, not mocked exceptions
- Test **integrations**: real SQLite with actual schema, in-memory database

### Test Database

Tests use in-memory SQLite (`:memory:`) for isolation. The test client fixture creates a fresh database for each test.

## Conventions

### UTC Timestamps

- **Storage:** ISO 8601 text in SQLite (e.g., `2025-12-22T10:30:00Z`)
- **Transaction dates:** DATE only (e.g., `2025-12-22`)
- **Timezone:** Always use UTC, never local time

### Error Handling

All exceptions inherit from base `MemoGardenError`:

- `ResourceNotFound` - Entity not found (404)
- `ValidationError` - Request validation failed (400)
- `DatabaseError` - Database operation failed (500)

---

**Last Updated:** 2025-12-24
**For:** MemoGarden Core maintainers
