"""Shared test fixtures for memogarden-core."""

import pytest
import sqlite3
from pathlib import Path
from memogarden_core.main import app


@pytest.fixture
def test_db():
    """Create in-memory test database with schema."""
    # Use in-memory database for tests
    db_path = ":memory:"

    # Create database with schema
    schema_path = Path(__file__).parent.parent / "memogarden_core" / "schema" / "schema.sql"

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    # Enable foreign key constraints (required for SQLite)
    db.execute("PRAGMA foreign_keys = ON")

    # Load and execute schema
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    db.executescript(schema_sql)
    db.commit()

    yield db

    # Cleanup
    db.close()


@pytest.fixture
def client():
    """Create test client for API testing."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
