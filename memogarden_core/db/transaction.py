"""Transaction-specific operations.

IMPORT CONVENTION:
- Core accesses these through core.transaction property
- Receives Core reference for coordinating entity registry operations

ID GENERATION POLICY:
All transaction IDs are auto-generated via entity.create(). This design:
1. Prevents users from accidentally passing invalid or duplicate IDs
2. Ensures entity registry entry is always created with transaction
3. Encapsulates ID generation logic within the database layer
4. Simplifies the API - users call core.transaction.create() without managing IDs
"""

import sqlite3
from datetime import date
from typing import Any, TYPE_CHECKING

from . import query
from ..utils import isodatetime
from ..exceptions import ResourceNotFound

if TYPE_CHECKING:
    from . import Core


class TransactionOperations:
    """Transaction operations.

    Coordinates with EntityOperations through Core reference.
    Automatically creates entity registry entries via core.entity.create().
    """

    def __init__(self, conn: sqlite3.Connection, core: "Core | None" = None):
        """Initialize transaction operations.

        Args:
            conn: SQLite connection with row_factory set to sqlite3.Row
            core: Core reference for coordinating entity registry operations.
                  Required for create() to auto-generate entity IDs.
        """
        self._conn = conn
        self._core = core

    def get_by_id(self, transaction_id: str) -> sqlite3.Row:
        """Get transaction by ID.

        Args:
            transaction_id: The UUID of the transaction

        Returns:
            sqlite3.Row with transaction data from transactions_view

        Raises:
            ResourceNotFound: If transaction_id doesn't exist
        """
        row = self._conn.execute(
            "SELECT * FROM transactions_view WHERE id = ?",
            (transaction_id,)
        ).fetchone()

        if not row:
            raise ResourceNotFound(
                f"Transaction '{transaction_id}' not found",
                {"transaction_id": transaction_id}
            )

        return row

    def create(
        self,
        amount: float,
        transaction_date: date,
        description: str,
        account: str,
        category: str | None = None,
        notes: str | None = None,
        author: str = "system"
    ) -> str:
        """Create a transaction with automatic entity registry creation.

        Creates both the entity registry entry and transaction record.
        The transaction ID is auto-generated via core.entity.create().

        Args:
            amount: Transaction amount
            transaction_date: Date of the transaction
            description: Short description/title
            account: Account label
            category: Optional category label
            notes: Optional detailed notes
            author: Creator identifier (default: "system")

        Returns:
            The auto-generated transaction ID (UUID v4 string)

        Raises:
            ValueError: If TransactionOperations initialized without Core reference
            sqlite3.IntegrityError: If generated UUID already exists (extremely rare)
        """
        if self._core is None:
            raise ValueError(
                "TransactionOperations requires Core reference for create(). "
                "Use core.transaction.create() instead of standalone TransactionOperations."
            )

        # Create entity registry entry (auto-generates UUID)
        transaction_id = self._core.entity.create("transactions")

        date_str = isodatetime.to_datestring(transaction_date)

        self._conn.execute(
            """INSERT INTO transactions
               (id, amount, currency, transaction_date, description, account, category, author, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (transaction_id, amount, "SGD", date_str, description, account, category, author, notes)
        )

        return transaction_id

    def list(
        self,
        filters: dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> list[sqlite3.Row]:
        """List transactions with filtering.

        Args:
            filters: Dictionary of filter conditions:
                - start_date: ISO 8601 date string (inclusive)
                - end_date: ISO 8601 date string (inclusive)
                - account: Account label
                - category: Category label
                - include_superseded: If False (default), excludes superseded transactions
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip (default: 0)

        Returns:
            List of sqlite3.Row objects with transaction data
        """
        param_map = {
            "start_date": "t.transaction_date >= ?",
            "end_date": "t.transaction_date <= ?",
            "account": "t.account = ?",
            "category": "t.category = ?",
        }

        # Filter out None values and exclude non-column flags like include_superseded
        conditions = {
            k: v for k, v in filters.items()
            if v is not None and k != "include_superseded"
        }

        where_clause, params = query.build_where_clause(conditions, param_map)

        # Handle superseded filter as special case (exclude if not explicitly included)
        # This is added separately because "IS NULL" doesn't use a placeholder
        if not filters.get("include_superseded"):
            if where_clause == "1=1":
                where_clause = "e.superseded_by IS NULL"
            else:
                where_clause += " AND e.superseded_by IS NULL"
        params.extend([limit, offset])

        query_sql = f"""
            SELECT t.*,
                   e.created_at, e.updated_at, e.superseded_by, e.superseded_at,
                   e.group_id, e.derived_from
            FROM transactions t
            JOIN entity e ON t.id = e.id
            WHERE {where_clause}
            ORDER BY t.transaction_date DESC, e.created_at DESC
            LIMIT ? OFFSET ?
        """

        return self._conn.execute(query_sql, params).fetchall()

    def update(self, transaction_id: str, data: dict[str, Any]) -> None:
        """Update transaction with partial data.

        Args:
            transaction_id: The UUID of the transaction to update
            data: Dictionary of field names to values to update

        Note:
            - Only non-None fields in data are updated
            - 'id' field is always excluded from updates
            - entity.updated_at is also updated
        """
        # Convert date to string if present
        if "transaction_date" in data and data["transaction_date"] is not None:
            data["transaction_date"] = isodatetime.to_datestring(data["transaction_date"])

        # Build UPDATE clause
        update_clause, params = query.build_update_clause(
            data,
            exclude={"id"}
        )

        if update_clause:
            params.append(transaction_id)

            # Update transaction
            self._conn.execute(
                f"UPDATE transactions SET {update_clause} WHERE id = ?",
                params
            )

            # Update entity registry timestamp
            # Note: Could delegate to core.entity.update_timestamp() after Core integration
            now = isodatetime.now()
            self._conn.execute(
                "UPDATE entity SET updated_at = ? WHERE id = ?",
                (now, transaction_id)
            )
