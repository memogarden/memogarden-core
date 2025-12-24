"""Shared test fixtures for memogarden-core."""

import pytest
import sqlite3
from pathlib import Path
from memogarden_core.main import app
from memogarden_core.config import settings


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
    """Create test client for API testing.

    Uses shared in-memory database to avoid file locking issues during tests.
    Each test gets a fresh database.
    """
    # Use a temp file database instead of :memory: for proper sharing
    import tempfile
    import os

    # Create temp file for database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Override database path
        original_db_path = settings.database_path
        settings.database_path = db_path

        # Initialize the database with schema
        from memogarden_core.db import init_db
        init_db()

        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    finally:
        # Restore original database path
        settings.database_path = original_db_path

        # Clean up temp file
        try:
            os.unlink(db_path)
        except:
            pass
