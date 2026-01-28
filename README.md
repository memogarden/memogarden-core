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
   poetry run python -m memogarden.db.seed
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
poetry run flask --app memogarden.main run --debug

# Production mode with gunicorn
poetry run gunicorn memogarden.main:app

# Or in poetry shell
poetry shell
flask --app memogarden.main run --debug
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
poetry run pytest --cov=memogarden

# Run specific test file
poetry run pytest tests/api/test_transactions.py

# Run with verbose output
poetry run pytest -v
```

**Test Coverage:** 394 tests passing, 91% coverage (exceeds 80% target)

### Manual Testing

For manual testing of the complete authentication and API flow:

#### 1. Start the development server

```bash
# From memogarden-core directory
poetry run flask --app memogarden.main run --debug

# Server will be available at http://localhost:5000
```

#### 2. Initial admin setup (first time only)

1. Open browser to: http://localhost:5000
2. You'll be redirected to admin registration page (localhost only)
3. Create admin account (username + password)
4. After registration, you'll be redirected to login

#### 3. Test authentication flow

**Via Web UI:**
- Login at http://localhost:5000/login
- Visit settings page: http://localhost:5000/settings (shows user info + token expiry)
- Manage API keys: http://localhost:5000/api-keys (list, create, revoke)

**Via API:**
```bash
# Login and get JWT token
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}' \
  -s | jq .

# Save the token for subsequent requests
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Test protected endpoint with JWT
curl http://localhost:5000/api/v1/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq .

# Test /auth/me endpoint
curl http://localhost:5000/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq .
```

#### 4. Test API key creation and usage

```bash
# Create an API key (via JWT token)
curl -X POST http://localhost:5000/api-keys/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-script", "expires_at": null}' \
  -s | jq .

# Save the full API key (only shown once!)
export API_KEY="mg_sk_agent_abc123def456..."

# Test API key authentication
curl http://localhost:5000/api/v1/transactions \
  -H "X-API-Key: $API_KEY" \
  -s | jq .

# List your API keys
curl http://localhost:5000/api-keys/ \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq .
```

#### 5. Test transaction endpoints

```bash
# Create a transaction
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": -15.50,
    "currency": "SGD",
    "transaction_date": "2025-12-29",
    "description": "Manual test transaction",
    "account": "Personal",
    "category": "Food"
  }' \
  -s | jq .

# List all transactions
curl http://localhost:5000/api/v1/transactions \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq .

# Get distinct labels
curl http://localhost:5000/api/v1/transactions/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq .

curl http://localhost:5000/api/v1/transactions/categories \
  -H "Authorization: Bearer $TOKEN" \
  -s | jq .
```

#### 6. Test authentication enforcement

```bash
# Test that unauthenticated requests are rejected
curl http://localhost:5000/api/v1/transactions
# Expected: 401 Unauthorized

# Test with invalid token
curl http://localhost:5000/api/v1/transactions \
  -H "Authorization: Bearer invalid_token"
# Expected: 401 Unauthorized

# Test with invalid API key
curl http://localhost:5000/api/v1/transactions \
  -H "X-API-Key: invalid_key"
# Expected: 401 Unauthorized
```

#### Manual Testing Checklist

- [ ] Admin registration page loads (localhost only)
- [ ] Admin account created successfully
- [ ] Login page accepts valid credentials
- [ ] Login rejects invalid credentials
- [ ] Settings page shows user info and token expiry
- [ ] API key creation works (full key shown once)
- [ ] API key listing works (no full keys shown)
- [ ] API key revocation works
- [ ] JWT authentication works for API endpoints
- [ ] API key authentication works for API endpoints
- [ ] Unauthenticated requests return 401
- [ ] Invalid tokens return 401
- [ ] Invalid API keys return 401
- [ ] Transaction creation works with auth
- [ ] Transaction listing works with auth
- [ ] Filter endpoints (accounts, categories) work with auth
- [ ] Health check works without auth (public endpoint)

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

All transaction endpoints require authentication. Use either:
- JWT Token: `Authorization: Bearer <token>`
- API Key: `X-API-Key: <api_key>`

#### Create Transaction

```bash
# With JWT Token
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "amount": -15.50,
    "currency": "SGD",
    "transaction_date": "2025-12-27",
    "description": "Coffee at Starbucks",
    "account": "Personal",
    "category": "Food"
  }'

# With API Key
curl -X POST http://localhost:5000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mg_sk_agent_abc123def456..." \
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
├── memogarden/
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
- `JWT_SECRET_KEY` - Secret key for JWT token signing (default: `change-me-in-production-use-env-var`)
- `JWT_EXPIRY_DAYS` - JWT token expiry in days (default: `30`)
- `BYPASS_LOCALHOST_CHECK` - Bypass localhost checks for testing only (default: `false`)

## Authentication

MemoGarden Core supports two authentication methods:

1. **JWT Tokens** - For interactive clients (Flutter app, web UI)
2. **API Keys** - For agents and scripts (programmatic access)

### Initial Setup

When you first start the API, you'll need to create an admin account. The admin registration endpoint is only accessible from localhost and only works once.

1. Start the API server:
   ```bash
   poetry run flask --app memogarden.main run --debug
   ```

2. Open your browser to: http://localhost:5000

3. You'll be redirected to the admin registration page. Create your admin account.

4. After registration, you can login at: http://localhost:5000/login

### JWT Token Authentication

#### Login

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

Response (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid",
    "username": "your_username",
    "is_admin": true
  }
}
```

#### Using JWT Token

Include the token in the Authorization header:

```bash
curl http://localhost:5000/api/v1/transactions \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Get Current User Info

```bash
curl http://localhost:5000/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Response (200 OK):
```json
{
  "id": "user-uuid",
  "username": "your_username",
  "is_admin": true,
  "created_at": "2025-12-29T10:00:00Z"
}
```

### API Key Authentication

API keys are recommended for agents, scripts, and programmatic access.

#### Create an API Key

```bash
curl -X POST http://localhost:5000/api-keys/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-script",
    "expires_at": null
  }'
```

Response (201 Created):
```json
{
  "id": "api-key-uuid",
  "name": "my-script",
  "key_prefix": "mg_sk_agent_abc1",
  "key": "mg_sk_agent_abc123def456...full_key_only_shown_once",
  "expires_at": null,
  "created_at": "2025-12-29T10:00:00Z"
}
```

**Important:** Copy the `key` value immediately. It will not be shown again.

#### Using API Key

Include the API key in the `X-API-Key` header:

```bash
curl http://localhost:5000/api/v1/transactions \
  -H "X-API-Key: mg_sk_agent_abc123def456..."
```

#### List API Keys

```bash
curl http://localhost:5000/api-keys/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response (200 OK):
```json
{
  "api_keys": [
    {
      "id": "api-key-uuid",
      "name": "my-script",
      "key_prefix": "mg_sk_agent_abc1",
      "expires_at": null,
      "created_at": "2025-12-29T10:00:00Z",
      "last_seen": "2025-12-29T12:30:00Z",
      "revoked_at": null
    }
  ]
}
```

#### Revoke API Key

```bash
curl -X DELETE http://localhost:5000/api-keys/{api_key_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response (204 No Content): API key revoked successfully.

## Current Implementation Status

**Completed (Step 1 - Core Backend Foundation):**
- ✅ Step 1.1: Project Setup & Structure
- ✅ Step 1.2: SQLite Database Schema (with entity registry)
- ✅ Step 1.3: Pydantic Schemas (API Validation)
- ✅ Step 1.4: Flask Application & Configuration
- ✅ Step 1.5: Transaction CRUD API Endpoints (7 endpoints)
- ✅ Step 1.6: Testing Infrastructure (385 tests, 90% coverage)
- ✅ Step 1.6.5: Schema Extension & Migration Design (docs in `/plan/future/`)

**Completed (Step 2 - Authentication & Multi-User Support):**
- ✅ Step 2.1: Database Schema: Users and API Keys
- ✅ Step 2.2: Pydantic Schemas (User, APIKey, Auth)
- ✅ Step 2.3: JWT Token Service
- ✅ Step 2.4: Authentication Endpoints (login, logout, /me, admin registration)
- ✅ Step 2.5: API Key Management Endpoints
- ✅ Step 2.6: Authentication Decorators (@localhost_only, @first_time_only)
- ✅ Step 2.7: HTML UI Pages (login, settings, API keys management)
- ✅ Step 2.8: Testing Infrastructure (139 auth tests, 94% coverage)
- ✅ Step 2.9: Documentation & Integration (API-level authentication, updated README)

**Current Work:**
- 🔄 Step 2.10: Refactor & Test Profiling (in progress - optimize test suite to <2.8s)

**Next Steps:**
- 📋 Step 3: Advanced Core Features (Recurrences, Relations, Deltas)

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

4. **Check coverage** if needed: `poetry run pytest --cov=memogarden`

5. **Commit** with clear messages describing what and why

## Production Deployment

### Quick Install (Linux / Raspberry Pi)

An automated install script is provided for Debian-based systems (Ubuntu, Raspberry Pi OS):

```bash
# Clone the repository
git clone https://github.com/memogarden/memogarden-core.git
cd memogarden-core

# Run install script (requires sudo)
sudo ./install.sh
```

The install script will:
1. Check prerequisites (Python 3.13+, git)
2. Install Poetry if not present
3. Install Python dependencies
4. Create `.env` with generated `JWT_SECRET_KEY`
5. Initialize the database
6. Create and enable systemd service
7. Start the service

### What Gets Installed

| Artifact | Location | Purpose |
|----------|----------|---------|
| Application | `/opt/memogarden-core/` (or wherever you cloned) | Code and virtual environment |
| Config | `./data/.env` | Environment variables |
| Database | `./data/memogarden.db` | SQLite database |
| Systemd service | `/etc/systemd/system/memogarden-core.service` | Auto-start on boot |
| Logs | `journalctl -u memogarden-core` | Service logs |

### Service Management

```bash
# Check service status
sudo systemctl status memogarden-core

# View logs (follow)
sudo journalctl -u memogarden-core -f

# Restart service
sudo systemctl restart memogarden-core

# Stop service
sudo systemctl stop memogarden-core

# Disable auto-start on boot
sudo systemctl disable memogarden-core
```

### Updating Deployment

After a `git pull`, simply reinstall:

```bash
cd memogarden-core
git pull
sudo ./install.sh
```

The script will:
- Backup existing `.env` to `.env.backup.YYYYMMDD_HHMMSS`
- Preserve your existing configuration
- Restart the service with new code

### Manual Setup (Without Install Script)

If you prefer manual setup or need custom configuration:

1. **Install dependencies:**
   ```bash
   sudo apt update
   sudo apt install python3.13 python3.13-venv git curl
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Clone and install:**
   ```bash
   git clone https://github.com/memogarden/memogarden-core.git
   cd memogarden-core
   poetry install
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env  # Set JWT_SECRET_KEY
   ```

4. **Initialize database:**
   ```bash
   poetry run python -m memogarden.db.seed
   ```

5. **Create systemd service** (see service file template below)

### Systemd Service Template

For manual systemd configuration, create `/etc/systemd/system/memogarden-core.service`:

```ini
[Unit]
Description=MemoGarden Core API
After=network.target

[Service]
Type=notify
User=your-user
Group=your-user
WorkingDirectory=/opt/memogarden-core
EnvironmentFile=/opt/memogarden-core/.env
ExecStart=/opt/memogarden-core/.venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    memogarden.main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Note: Poetry must be configured to use in-project venvs: `poetry config virtualenvs.in-project true`

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable memogarden-core
sudo systemctl start memogarden-core
```

### Production Considerations

**For Tailscale-only deployment (current default):**
- `CORS_ORIGINS=["*"]` is acceptable
- No reverse proxy needed
- JWT tokens over Tailscale's encrypted tunnel

**For public deployment (future):**
- Restrict `CORS_ORIGINS` to specific domains
- Add nginx reverse proxy for HTTPS
- Set strong `JWT_SECRET_KEY`
- Implement database backups
- Consider rate limiting

### Troubleshooting

**Service won't start:**
```bash
# Check detailed logs
sudo journalctl -u memogarden-core -n 100

# Check if port is already in use
sudo ss -tlnp | grep 5000
```

**Database errors:**
```bash
# Check database exists and is writable
ls -la ./data/memogarden.db

# Reinitialize if needed (WARNING: destroys data)
rm ./data/memogarden.db
poetry run python -m memogarden.db.seed
```

**Permission errors:**
```bash
# Ensure service user owns the data directory
sudo chown -R $USER:$USER ./data
```

## Contributing

This is a personal project, but issues and suggestions are welcome.

## License

TBD
