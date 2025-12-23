"""Database connection layer using sqlite3."""

import sqlite3
from pathlib import Path
from flask import g
from .config import settings
from .utils import isodatetime, uid


def get_db() -> sqlite3.Connection:
    """
    Get database connection for current request.

    Uses Flask's g object to store connection per request.
    Connection is automatically closed at request end.

    Returns:
        SQLite database connection with Row factory.
    """
    if 'db' not in g:
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        g.db = sqlite3.connect(str(db_path))
        g.db.row_factory = sqlite3.Row
        # Enable foreign key constraints (required for SQLite)
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(e=None):
    """
    Close database connection at end of request.

    Registered with Flask's teardown_appcontext to run automatically.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """
    Initialize database by running schema.sql if not already initialized.

    For fresh databases: applies current schema from schema.sql.
    For existing databases: skips initialization (migrations handled separately in Step 3+).
    """
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as db:
        # Check if database is already initialized
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_metadata'"
        )
        if cursor.fetchone():
            # Database already initialized, skip
            return

        # Fresh database - apply current schema
        schema_path = Path(__file__).parent.parent / "schema" / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            db.executescript(schema_sql)
            db.commit()


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
        entity_id = uid.generate_uuid()

    now = isodatetime.now()

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
    now = isodatetime.now()

    db.execute(
        """UPDATE entity
           SET superseded_by = ?, superseded_at = ?, updated_at = ?
           WHERE id = ?""",
        (new_id, now, now, old_id)
    )
