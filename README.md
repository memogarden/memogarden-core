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
```

## Project Structure

```
memogarden-core/
├── memogarden_core/
│   ├── __init__.py
│   ├── main.py              # Flask app
│   ├── config.py            # Settings with pydantic-settings
│   ├── database.py          # sqlite3 connection & entity helpers
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql       # SOURCE OF TRUTH for database
│   │   ├── seed.py          # Seed data script
│   │   └── migrations/      # Future migration scripts
│   ├── schemas/             # Pydantic models (API validation only)
│   │   ├── __init__.py
│   │   └── transaction.py   # TransactionCreate, Update, Response
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── transactions.py  # (to be implemented)
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures (use :memory: SQLite)
│   ├── test_config.py       # Configuration tests
│   ├── test_database.py     # Database & entity registry tests
│   ├── test_schemas.py      # Pydantic schema validation tests
│   └── api/
│       └── test_health.py   # Health endpoint tests
├── data/
│   └── .gitignore           # Ignore *.db files
├── .env.example
├── .gitignore
├── README.md
└── pyproject.toml
```

## Environment Variables

See [.env.example](.env.example) for all available configuration options.

## Current Implementation Status

**Completed:**
- ✅ Step 1.1: Project Setup & Structure
- ✅ Step 1.2: SQLite Database Schema (with entity registry)
- ✅ Step 1.3: Pydantic Schemas (API Validation)

**Next:**
- 🔄 Step 1.4: Flask Application & Configuration
- ⏳ Step 1.5: API Endpoints Implementation
- ⏳ Step 1.6: Testing Infrastructure
- ⏳ Step 1.7: Documentation & Development Workflow

See [plan/implementation.md](../plan/implementation.md) for detailed progress.

## Core Philosophy

1. **Transactions Are Beliefs** - A transaction represents the user's understanding at the time of payment, not the bank's ledger
2. **Single Source of Truth** - All transactions flow through MemoGarden Core API
3. **Mutable Snapshot, Immutable Memory** - Current state can change, but all changes are logged via deltas
4. **Document-Centric Traceability** - Transactions link to immutable artifacts in Soil (emails, invoices, statements)
5. **Agent-First Design** - Humans and agents use the same APIs

## Contributing

This is a personal project, but issues and suggestions are welcome.

## License

TBD
