# MemoGarden Core - Development Guide

This document describes the major patterns, conventions, and decisions used in MemoGarden Core development. It serves as a practical guide for contributors and AI agents working on the codebase.

**Last Updated:** 2025-12-29

---

## Table of Contents

1. [Utility Modules](#utility-modules)
2. [Import Conventions](#import-conventions)
3. [Date and Time Handling](#date-and-time-handling)
4. [Type Definitions](#type-definitions)
5. [External Dependencies](#external-dependencies)
6. [Testing Conventions](#testing-conventions)

---

## Utility Modules

MemoGarden Core uses centralized utility modules to ensure consistency and make dependencies explicit.

### `utils/isodatetime` - Date/Time Operations

**All date/time operations MUST use the `isodatetime` module.**

```python
from memogarden_core.utils import isodatetime

# Get current UTC timestamp as ISO string
timestamp = isodatetime.now()  # "2025-12-29T10:30:00Z"

# Get current Unix timestamp (for JWT, external APIs)
unix_ts = isodatetime.now_unix()  # 1735460500

# Convert datetime to ISO string
iso_str = isodatetime.to_timestamp(datetime_obj)

# Convert ISO string to datetime
dt = isodatetime.to_datetime("2025-12-29T10:30:00Z")

# Convert date to ISO date string
date_str = isodatetime.to_datestring(date_obj)

# Unix timestamp conversions (for JWT, external systems)
unix_ts = isodatetime.to_unix_timestamp(datetime_obj)
dt = isodatetime.from_unix_timestamp(1735460500)
```

**DO NOT import `datetime` directly in business logic:**
```python
# ❌ AVOID - loose datetime import
from datetime import datetime, UTC
now = datetime.now(UTC)

# ✅ PREFERRED - use isodatetime
from memogarden_core.utils import isodatetime
now_ts = isodatetime.now_unix()
```

**Exception:** Tests may import `datetime` and `timedelta` for test data, but should use `isodatetime` for getting current time.

### `utils/uid` - UUID Generation

**DEPRECATED:** For new code, use `utils.secret.generate_uuid()` instead (see below).

This module is maintained for backward compatibility:

```python
from memogarden_core.utils import uid

user_id = uid.generate_uuid()  # "550e8400-e29b-41d4-a716-446655440000"
```

### `utils/secret` - Secret Generation

**ALL secret and UUID generation MUST use the `secret` module:**

```python
from memogarden_core.utils import secret

# Generate UUID for entities
user_id = secret.generate_uuid()
api_key_id = secret.generate_uuid()

# Generate API keys
api_key = secret.generate_api_key()  # "mg_sk_agent_abc123..."

# Generate random tokens (password reset, etc.)
token = secret.generate_token()  # 64-character hex token
short_token = secret.generate_token(num_bytes=16)  # 32-character hex token

# Generate random passwords
password = secret.generate_password()  # 16 characters
short_password = secret.generate_password(length=12)  # 12 characters
```

**DO NOT import `uuid4` or `secrets` directly:**
```python
# ❌ AVOID - direct uuid/secrets imports
from uuid import uuid4
import secrets
user_id = str(uuid4())
api_key = secrets.token_hex(32)

# ✅ PREFERRED - use secret utility
from memogarden_core.utils import secret
user_id = secret.generate_uuid()
api_key = secret.generate_api_key()
```

This approach:
- Confines third-party crypto imports (`uuid`, `secrets`) to one module
- Makes it easy to audit all secret generation in the codebase
- Provides a single place to update secret generation algorithms

---

## Import Conventions

### Module-Level Imports

For first-party modules (`utils.*`, `db.*`, etc.), use **module-level imports**:

```python
# ✅ PREFERRED
from memogarden_core.utils import isodatetime, secret
from memogarden_core.db import get_core

timestamp = isodatetime.now()
uuid = secret.generate_uuid()
api_key = secret.generate_api_key()
```

This provides:
- Clear namespace usage (`isodatetime.now()` vs `now()`)
- Better IDE navigation
- Explicit dependency tracking

### Third-Party Libraries

Import third-party libraries normally:
```python
import jwt as pyjwt  # Alias to avoid conflicts
from flask import Flask, request
from pydantic import BaseModel
```

---

## Date and Time Handling

### UTC Everywhere

**All timestamps MUST be in UTC.**

- Storage: ISO 8601 text with `Z` suffix (`2025-12-29T10:30:00Z`)
- Timezone: Always UTC, never local time
- Unix timestamps: Seconds since epoch in UTC

### Domain Types

Use `schema/types.py` domain types for type safety:

```python
from memogarden_core.schema.types import Timestamp, Date

# Get current timestamp
now = Timestamp.now()  # "2025-12-29T10:30:00Z"

# Create from datetime
ts = Timestamp.from_datetime(datetime_obj)

# Convert back to datetime
dt = ts.to_datetime()

# Date handling
today = Date.today()  # "2025-12-29"
d = Date.from_date(date_obj)
date_obj = d.to_date()
```

### When to Use Which

| Use Case | Approach |
|----------|----------|
| Database storage / API response | `isodatetime.now()` → ISO string |
| JWT tokens / external APIs | `isodatetime.now_unix()` → Unix timestamp |
| Domain logic with type safety | `Timestamp.now()`, `Date.today()` |
| Test data creation | `datetime(2025, 12, 29, 10, 30, 0)` (naive OK) |

---

## Type Definitions

### Domain Types (`schema/types.py`)

Domain types are **string subtypes** for JSON compatibility:

```python
class Timestamp(str):
    """ISO 8601 UTC timestamp string."""

class Date(str):
    """ISO 8601 date string."""
```

**Use domain types when:**
- Type safety is important (API schemas, domain logic)
- You need conversion helpers (`.to_datetime()`, `.to_date()`)
- Working with entities or API responses

**Use plain strings when:**
- Simple value passing
- Performance-critical code (avoid conversion overhead)

### Pydantic Schemas

Use Pydantic for API validation:

```python
from pydantic import BaseModel
from memogarden_core.schema.types import Timestamp

class UserResponse(BaseModel):
    id: str
    username: str
    is_admin: bool
    created_at: Timestamp  # Domain type for validation
```

---

## External Dependencies

### Dependency Confinement

**Confine external dependencies to single modules when possible.**

Example: JWT tokens
```python
# ✅ Only auth/token.py imports PyJWT
from memogarden_core.auth.token import generate_access_token

# Other modules use the abstraction, never import jwt directly
token = generate_access_token(user)
```

**Benefits:**
- Easy to swap implementations
- Clear upgrade path
- Reduced coupling to external APIs

### Adding New Dependencies

Before adding a new dependency:

1. **Check if existing utilities can solve it** (isodatetime, uid, schema types)
2. **Prefer standard library** over third-party packages
3. **Create abstraction layer** if dependency is complex
4. **Document the decision** in this guide

---

## Testing Conventions

### No Mocks

**Avoid mocks, monkeypatching, and test doubles.**

Tests should verify **observable behavior**:
- API inputs → outputs
- Database state changes
- Error conditions (real errors, not mocked)

Use **in-memory SQLite** `:memory:` for database tests.

### Test Data

For test data, direct `datetime` imports are acceptable:

```python
from datetime import datetime

user = UserResponse(
    id="550e8400-e29b-41d4-a716-446655440000",
    created_at=datetime(2025, 12, 29, 10, 30, 0),  # OK for test data
)
```

But use `isodatetime` for **current time assertions**:

```python
from memogarden_core.utils import isodatetime

before_ts = isodatetime.now_unix()
# ... run code ...
after_ts = isodatetime.now_unix()

assert before_ts <= result_iat <= after_ts
```

### Test Organization

- **Behavior-focused tests survive refactoring**
- Test **what** (observable behavior), not **how** (implementation)
- One assertion per test concept (multiple OK if related)

---

## File Structure

```
memogarden-core/
├── memogarden_core/
│   ├── utils/          # Utility modules (isodatetime, uid)
│   ├── schema/         # Database schema, types
│   ├── db/             # Database operations (get_core)
│   ├── api/            # API endpoints
│   ├── auth/           # Authentication module
│   └── config.py       # Configuration (Settings)
├── tests/              # Tests mirror src structure
├── docs/               # Documentation (this guide, architecture.md)
└── scripts/            # Convenience scripts
```

---

## Common Patterns

### Database Operations

```python
from memogarden_core.db import get_core

core = get_core()
transaction = core.transaction.get_by_id(uuid)
```

### Configuration

```python
from memogarden_core.config import settings

# Access via settings object
db_path = settings.database_path
secret = settings.jwt_secret_key
```

### API Validation

```python
from memogarden_core.api.v1.decorators import validate_request

@app.post("/transactions")
@validate_request
def create_transaction(data: TransactionCreate):
    # data is already validated
    ...
```

---

## Code Review Checklist

When reviewing code (or using AI assistants), check:

- [ ] No loose `datetime` imports (use `isodatetime`)
- [ ] No direct `uuid4` imports (use `uid.generate_uuid()`)
- [ ] External dependencies confined to single modules
- [ ] UTC timestamps everywhere
- [ ] Domain types used for type safety
- [ ] Tests follow behavior-focused approach (no mocks)
- [ ] Module-level imports for first-party code
- [ ] Docstrings on public functions/classes

---

## References

- **[architecture.md](architecture.md)** - Technical architecture and design patterns
- **[../plan/implementation.md](../../plan/implementation.md)** - Implementation plan and progress
- **[../plan/prd.md](../../plan/prd.md)** - Product requirements

---

**For questions or clarifications, update this guide.** Consistency is key to maintainable code.
