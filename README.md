# MemoGarden Core

Personal expenditure tracking API - A lightweight memory system for financial transactions.

## Overview

MemoGarden Core is the backend API for MemoGarden, a personal memory system for financial transactions. It's not traditional budgeting software—it's a belief-based transaction capture and reconciliation system designed for both human users and AI agents.

## Technology Stack

- **Language**: Python 3.13
- **Framework**: FastAPI (async/await)
- **Database**: SQLite (no ORM - raw SQL only)
- **Data Access**: aiosqlite for async operations
- **Validation**: Pydantic (API layer only, NOT as ORM)
- **Testing**: pytest with pytest-asyncio
- **Package Manager**: Poetry with poetry-plugin-shell

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
# Using Poetry script
poetry run dev

# Or directly with uvicorn
poetry run uvicorn memogarden_core.main:app --reload

# Or in poetry shell
poetry shell
uvicorn memogarden_core.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

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
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings with pydantic-settings
│   ├── database.py          # aiosqlite connection & helpers
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql       # SOURCE OF TRUTH for database
│   │   └── migrations/      # Optional migration scripts
│   ├── schemas/             # Pydantic models (API validation only)
│   │   ├── __init__.py
│   │   ├── transaction.py
│   │   ├── account.py
│   │   └── category.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── transactions.py
│   │       ├── accounts.py
│   │       └── categories.py
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures (use :memory: SQLite)
│   └── api/
│       └── test_transactions.py
├── data/
│   └── .gitignore           # Ignore *.db files
├── .env.example
├── .gitignore
├── README.md
└── pyproject.toml
```

## Environment Variables

See [.env.example](.env.example) for all available configuration options.

## API Documentation

Once the server is running, visit http://localhost:8000/docs for interactive API documentation powered by FastAPI's automatic OpenAPI generation.

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
