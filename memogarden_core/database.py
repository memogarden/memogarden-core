"""Database connection layer using sqlite3."""

import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime, UTC
from .config import settings


_db_connection = None


def get_db() -> sqlite3.Connection:
    """
    Get database connection.

    Returns connection to SQLite database.
    """
    global _db_connection
    if _db_connection is None:
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db_connection = sqlite3.connect(str(db_path))
        _db_connection.row_factory = sqlite3.Row
        # Enable foreign key constraints (required for SQLite)
        _db_connection.execute("PRAGMA foreign_keys = ON")
    return _db_connection


def init_db():
    """Initialize database by running schema.sql."""
    schema_path = Path(__file__).parent / "db" / "schema.sql"

    if schema_path.exists():
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(db_path)) as db:
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            db.executescript(schema_sql)
            db.commit()


def close_db():
    """Close database connection."""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None


def get_schema_version() -> str:
    """
    Get current schema version from _schema_metadata table.

    Returns:
        Schema version string (e.g., '20251223')
    """
    db = get_db()
    cursor = db.execute(
        "SELECT value FROM _schema_metadata WHERE key = 'version'"
    )
    row = cursor.fetchone()
    return row[0] if row else "unknown"


def create_entity(db: sqlite3.Connection, entity_type: str, entity_id: str | None = None) -> str:
    """
    Create entity in global registry.

    Args:
        db: Database connection
        entity_type: Type of entity (e.g., 'transactions', 'recurrences')
        entity_id: Optional UUID (will generate if not provided)

    Returns:
        Entity UUID (str)
    """
    if entity_id is None:
        entity_id = str(uuid4())

    now = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

    db.execute(
        """INSERT INTO entity (id, type, created_at, updated_at)
           VALUES (?, ?, ?, ?)""",
        (entity_id, entity_type, now, now)
    )

    return entity_id


def get_entity_type(db: sqlite3.Connection, entity_id: str) -> str | None:
    """
    Lookup entity type from registry.

    Args:
        db: Database connection
        entity_id: Entity UUID

    Returns:
        Entity type string or None if not found
    """
    cursor = db.execute(
        "SELECT type FROM entity WHERE id = ?",
        (entity_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def supersede_entity(db: sqlite3.Connection, old_id: str, new_id: str) -> None:
    """
    Mark entity as superseded by another entity.

    Args:
        db: Database connection
        old_id: UUID of entity being superseded
        new_id: UUID of superseding entity
    """
    now = datetime.now(UTC).isoformat().replace('+00:00', 'Z')

    db.execute(
        """UPDATE entity
           SET superseded_by = ?, superseded_at = ?, updated_at = ?
           WHERE id = ?""",
        (new_id, now, now, old_id)
    )
