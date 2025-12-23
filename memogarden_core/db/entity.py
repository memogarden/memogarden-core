"""Entity registry operations.

The entity registry provides a global table tracking all entities
in the system.

IMPORT CONVENTION:
- Core accesses these through core.entity property
- NO direct import needed when using Core API

ID GENERATION POLICY:
All entity IDs are auto-generated UUIDs. This design choice:
1. Prevents users from accidentally passing invalid or duplicate IDs
2. Encapsulates ID generation logic within the database layer
3. Ensures UUID v4 format compliance
4. Simplifies the API - users don't need to manage ID creation
"""

import sqlite3
from ..utils import uid, isodatetime
from ..exceptions import ResourceNotFound


class EntityOperations:
    """Entity registry operations.

    Provides methods for creating, retrieving, and managing entities
    in the global entity registry.
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize entity operations with a database connection.

        Args:
            conn: SQLite connection with row_factory set to sqlite3.Row
        """
        self._conn = conn

    def create(
        self,
        entity_type: str,
        group_id: str | None = None,
        derived_from: str | None = None
    ) -> str:
        """Create entity in global registry with auto-generated UUID.

        Args:
            entity_type: The type of entity (e.g., 'transactions', 'recurrences')
            group_id: Optional group ID for clustering related entities
            derived_from: Optional ID of source entity for provenance tracking

        Returns:
            The auto-generated entity ID (UUID v4 string)

        Raises:
            sqlite3.IntegrityError: If generated UUID already exists (extremely rare)
        """
        # Generate UUID with collision retry
        max_retries = 3
        for attempt in range(max_retries):
            entity_id = uid.generate_uuid()

            try:
                now = isodatetime.now()
                self._conn.execute(
                    """INSERT INTO entity (id, type, group_id, derived_from, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (entity_id, entity_type, group_id, derived_from, now, now)
                )
                return entity_id
            except sqlite3.IntegrityError:
                # UUID collision - retry with new UUID
                if attempt == max_retries - 1:
                    raise

        # Should never reach here
        raise RuntimeError("Failed to generate unique UUID after retries")

    def get_by_id(
        self,
        entity_id: str,
        table_or_view: str = "entity",
        entity_type: str = "Entity"
    ) -> sqlite3.Row:
        """Get entity by ID, raise ResourceNotFound if not found.

        Args:
            entity_id: The UUID of the entity
            table_or_view: Table or view name to query (default: 'entity')
            entity_type: Human-readable type name for error messages

        Returns:
            sqlite3.Row with entity data

        Raises:
            ResourceNotFound: If entity_id doesn't exist
        """
        row = self._conn.execute(
            f"SELECT * FROM {table_or_view} WHERE id = ?",
            (entity_id,)
        ).fetchone()

        if not row:
            raise ResourceNotFound(
                f"{entity_type} '{entity_id}' not found",
                {"entity_id": entity_id}
            )

        return row

    def supersede(self, old_id: str, new_id: str) -> None:
        """Mark entity as superseded by another entity.

        Args:
            old_id: The ID of the entity being superseded
            new_id: The ID of the superseding entity

        Note:
            Both entities should exist before calling this method.
            The old entity will have superseded_by and superseded_at set.
        """
        now = isodatetime.now()

        self._conn.execute(
            """UPDATE entity
               SET superseded_by = ?, superseded_at = ?, updated_at = ?
               WHERE id = ?""",
            (new_id, now, now, old_id)
        )

    def update_timestamp(self, entity_id: str) -> None:
        """Update the updated_at timestamp for an entity.

        Args:
            entity_id: The ID of the entity to update
        """
        now = isodatetime.now()

        self._conn.execute(
            "UPDATE entity SET updated_at = ? WHERE id = ?",
            (now, entity_id)
        )
