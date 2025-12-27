# MemoGarden Core

Personal expenditure tracking API - A lightweight memory system for financial transactions.

## Overview

MemoGarden Core is the backend API for MemoGarden, a personal memory system for financial transactions. It's not traditional budgeting software—it's a belief-based transaction capture and reconciliation system designed for both human users and AI agents.

## Technology Stack

- **Language**: Python 3.13
- **Framework**: Flask (synchronous)
- **Database**: SQLite (no ORM - raw SQL only)
- **Data Access**: Built-in sqlite3 module
- **Validation**: Pydantic (API layer only, NOT as ORM)
- **Testing**: pytest with pytest-flask
- **Package Manager**: Poetry with poetry-plugin-shell
- **Production Server**: gunicorn

## Prerequisites

- Python 3.13+
- Poetry (with poetry-plugin-shell)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/memogarden/memogarden-core.git
   cd memogarden-core
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

4. Initialize database:
   ```bash
   poetry run python -m memogarden_core.db.seed
   ```

## Development

### Running the API server

**Using convenience scripts (from parent directory):**
```bash
# From /home/kureshii/memogarden/
./scripts/run.sh              # Start development server
./scripts/test.sh             # Run tests
./scripts/test-coverage.sh    # Run tests with coverage
```

**Manual commands (from memogarden-core directory):**
```bash
# Development mode with Flask
poetry run flask --app memogarden_core.main run --debug

# Production mode with gunicorn
poetry run gunicorn memogarden_core.main:app

# Or in poetry shell
poetry shell
flask --app memogarden_core.main run --debug
```

The API will be available at:
- API: http://localhost:5000 (Flask default)
- Health check: http://localhost:5000/health
- API endpoints: http://localhost:5000/api/v1/...

### Running tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=memogarden_core

# Run specific test file
poetry run pytest tests/api/test_transactions.py

# Run with verbose output
poetry run pytest -v
```

**Test Coverage:** 231 tests passing, 90% coverage (exceeds 80% target)

## API Endpoints

### Health Check

```bash
curl http://localhost:5000/health
```

Response:
```json
{"status": "ok"}
```

### Transaction Endpoints

#### Create Transaction

```bash
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "amount": -15.50,
    "currency": "SGD",
    "transaction_date": "2025-12-27",
    "description": "Coffee at Starbucks",
    "account": "Personal",
    "category": "Food"
  }'
```

Response (201 Created):
```json
{
  "id": "uuid-here",
  "amount": -15.50,
  "currency": "SGD",
  "transaction_date": "2025-12-27",
  "description": "Coffee at Starbucks",
  "account": "Personal",
  "category": "Food",
  "author": "system",
  "notes": null,
  "recurrence_id": null,
  "created_at": "2025-12-27T12:00:00Z",
  "updated_at": "2025-12-27T12:00:00Z",
  "superseded_by": null,
  "group_id": null
}
```

#### List Transactions

```bash
# List all transactions
curl http://localhost:5000/api/v1/transactions

# Filter by date range
curl "http://localhost:5000/api/v1/transactions?start_date=2025-12-01&end_date=2025-12-31"

# Filter by account
curl "http://localhost:5000/api/v1/transactions?account=Personal"

# Filter by category
curl "http://localhost:5000/api/v1/transactions?category=Food"

# Pagination
curl "http://localhost:5000/api/v1/transactions?limit=10&offset=0"

# Combined filters
curl "http://localhost:5000/api/v1/transactions?account=Personal&category=Food&limit=5"
```

Response (200 OK):
```json
[
  {
    "id": "uuid-1",
    "amount": -15.50,
    "description": "Coffee at Starbucks",
    "account": "Personal",
    "category": "Food",
    "transaction_date": "2025-12-27",
    "created_at": "2025-12-27T12:00:00Z",
    ...
  }
]
```

#### Get Single Transaction

```bash
curl http://localhost:5000/api/v1/transactions/{id}
```

Response (200 OK): Single transaction object, or 404 if not found.

#### Update Transaction

```bash
curl -X PUT http://localhost:5000/api/v1/transactions/{id} \
  -H "Content-Type: application/json" \
  -d '{"amount": -16.00, "description": "Latte at Starbucks"}'
```

Response (200 OK): Updated transaction object.

#### Delete Transaction

```bash
curl -X DELETE http://localhost:5000/api/v1/transactions/{id}
```

Response (204 No Content): Transaction deleted successfully.

#### Label Utility Endpoints

```bash
# List all distinct account labels
curl http://localhost:5000/api/v1/transactions/accounts

# Response: ["Personal", "Household"]

# List all distinct category labels
curl http://localhost:5000/api/v1/transactions/categories

# Response: ["Food", "Transport", "Shopping", "Entertainment"]
```

## Project Structure

```
memogarden-core/
├── memogarden_core/
│   ├── __init__.py
│   ├── main.py              # Flask app with CORS, error handlers
│   ├── config.py            # Settings with pydantic-settings
│   ├── exceptions.py        # Custom exception classes
│   ├── db/
│   │   ├── __init__.py       # Core API: entity, transaction operations
│   │   ├── entity.py         # Entity registry operations
│   │   ├── transaction.py    # Transaction operations
│   │   ├── query.py          # Query builders
│   │   ├── seed.py           # Seed data script
│   │   ├── schema.sql        # SOURCE OF TRUTH for database
│   │   └── migrations/       # Future migration scripts
│   ├── schema/
│   │   ├── __init__.py
│   │   ├── schema.sql        # Database schema (moved to db/)
│   │   └── types.py          # Domain types: Timestamp, Date
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── transaction.py    # Pydantic models (API validation only)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── validation.py     # @validate_request decorator
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── schemas/      # Request/response schemas
│   │       │   └── transaction.py
│   │       └── transactions.py  # Transaction endpoints
│   └── utils/
│       ├── __init__.py
│       ├── isodatetime.py    # ISO 8601 utilities
│       └── uid.py            # UUID generation
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Test fixtures (test_db, client)
│   ├── test_*.py             # 231 tests, 90% coverage
│   └── api/
│       ├── test_transactions.py
│       ├── test_validation.py
│       └── test_health.py
├── data/
│   └── .gitignore           # Ignore *.db files
├── .env.example             # Environment variables template
├── .gitignore
├── README.md
└── pyproject.toml
```

## Environment Variables

See [.env.example](.env.example) for all available configuration options:

- `DATABASE_PATH` - Path to SQLite database file (default: `./data/memogarden.db`)
- `API_V1_PREFIX` - API v1 prefix (default: `/api/v1`)
- `CORS_ORIGINS` - Allowed CORS origins as JSON array (default: `["http://localhost:3000"]`)
- `DEFAULT_CURRENCY` - Default currency code (default: `SGD`)

## Current Implementation Status

**Completed (Step 1 - Core Backend Foundation):**
- ✅ Step 1.1: Project Setup & Structure
- ✅ Step 1.2: SQLite Database Schema (with entity registry)
- ✅ Step 1.3: Pydantic Schemas (API Validation)
- ✅ Step 1.4: Flask Application & Configuration
- ✅ Step 1.5: Transaction CRUD API Endpoints (7 endpoints)
- ✅ Step 1.6: Testing Infrastructure (231 tests, 90% coverage)
- ✅ Step 1.6.5: Schema Extension & Migration Design (docs in `/plan/future/`)

**Next Steps:**
- 🔄 Step 1.7: Documentation & Development Workflow (in progress)
- ⏳ Step 2: Authentication & Multi-User Support

See [plan/implementation.md](../plan/implementation.md) for detailed progress.

## Core Philosophy

1. **Transactions Are Beliefs** - A transaction represents the user's understanding at the time of payment, not the bank's ledger
2. **Single Source of Truth** - All transactions flow through MemoGarden Core API
3. **Mutable Snapshot, Immutable Memory** - Current state can change, but all changes are logged via deltas
4. **Document-Centric Traceability** - Transactions link to immutable artifacts in Soil (emails, invoices, statements)
5. **Agent-First Design** - Humans and agents use the same APIs

## Design Principles

- **Synchronous Execution** - Flask + sqlite3 for simplicity and deterministic debugging
- **No ORM** - Raw SQL queries with parameterized statements
- **Entity Registry** - Global metadata table for all entity types
- **Labels not Entities** - Accounts and categories are user-defined strings, not database entities
- **UTC Everywhere** - All timestamps in ISO 8601 UTC format
- **Test-Driven** - 90% test coverage with behavior-focused tests (no mocks)

## Development Workflow

1. **Always run from the correct directory:**
   - `/home/kureshii/memogarden/memogarden-core/` for Poetry commands
   - `/home/kureshii/memogarden/` for convenience scripts

2. **Make changes** to code

3. **Run tests** to verify: `poetry run pytest`

4. **Check coverage** if needed: `poetry run pytest --cov=memogarden_core`

5. **Commit** with clear messages describing what and why

## Contributing

This is a personal project, but issues and suggestions are welcome.

## License

TBD
