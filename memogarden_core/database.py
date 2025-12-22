"""Database connection layer using aiosqlite."""

import aiosqlite
from pathlib import Path
from .config import settings


_db_connection = None


async def get_db() -> aiosqlite.Connection:
    """
    Get database connection.

    Returns connection to SQLite database.
    """
    global _db_connection
    if _db_connection is None:
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db_connection = await aiosqlite.connect(str(db_path))
        _db_connection.row_factory = aiosqlite.Row
    return _db_connection


async def init_db():
    """Initialize database by running schema.sql."""
    db = await get_db()
    schema_path = Path(__file__).parent / "db" / "schema.sql"

    if schema_path.exists():
        async with aiosqlite.connect(settings.database_path) as db:
            with open(schema_path, "r") as f:
                schema_sql = f.read()
            await db.executescript(schema_sql)
            await db.commit()


async def close_db():
    """Close database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
