"""Shared test fixtures for memogarden-core."""

import os
import tempfile
import sqlite3
from pathlib import Path

import pytest
from flask import g

from memogarden_core.main import app
from memogarden_core.config import settings
from memogarden_core.auth import schemas, service, token as auth_token, api_keys


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


@pytest.fixture
def test_user(test_db):
    """Create a test user for authentication tests.

    Returns a tuple of (user, password) where user is the UserResponse schema
    and password is the plain text password.
    """
    password = "TestPass123"
    user_data = schemas.UserCreate(username="testuser", password=password)
    user = service.create_user(test_db, user_data, is_admin=False)
    test_db.commit()

    user_response = schemas.UserResponse(
        id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        created_at=user.created_at
    )

    return user_response, password


@pytest.fixture
def jwt_token(test_user):
    """Generate a JWT token for the test user.

    Returns the JWT token string.
    """
    user_response, _password = test_user
    return auth_token.generate_access_token(user_response)


@pytest.fixture
def auth_headers(jwt_token):
    """Get authentication headers with JWT token.

    Returns a dict with Authorization header set.
    """
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.fixture
def api_key(test_db, test_user):
    """Create an API key for the test user.

    Returns the APIKeyResponse schema.
    """
    user_response, _password = test_user
    api_key_data = schemas.APIKeyCreate(name="test-api-key", expires_at=None)
    api_key_result = api_keys.create_api_key(test_db, user_response.id, api_key_data)
    test_db.commit()

    return api_key_result


@pytest.fixture
def api_key_headers(api_key):
    """Get authentication headers with API key.

    Returns a dict with X-API-Key header set.
    """
    return {"X-API-Key": api_key.key}


@pytest.fixture
def authenticated_client():
    """Create an authenticated test client with JWT token.

    This fixture creates a test user and returns a client that can make
    authenticated requests using JWT token. The client will automatically
    include the Authorization header.

    Returns a tuple of (client, user, auth_headers) where:
    - client: Flask test client
    - user: UserResponse schema for the created user
    - auth_headers: dict with Authorization header
    """
    # Create temp file database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # Override database path
        original_db_path = settings.database_path
        settings.database_path = db_path

        # Initialize the database with schema
        from memogarden_core.db import init_db, get_core
        init_db()

        # Create a test user in the database
        core = get_core()
        password = "TestPass123"
        user_data = schemas.UserCreate(username="testuser", password=password)
        user = service.create_user(core._conn, user_data, is_admin=False)
        core._conn.commit()

        # Generate JWT token
        user_response = schemas.UserResponse(
            id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
        jwt_token = auth_token.generate_access_token(user_response)

        # Create auth headers
        auth_headers = {"Authorization": f"Bearer {jwt_token}"}

        # Create test client
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client, user_response, auth_headers

    finally:
        # Restore original database path
        settings.database_path = original_db_path

        # Clean up temp file
        try:
            os.unlink(db_path)
        except:
            pass
