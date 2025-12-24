"""Transaction CRUD endpoints for MemoGarden Core API.

This module implements RESTful endpoints for transaction management:
- POST   /api/v1/transactions                 - Create transaction
- GET    /api/v1/transactions                 - List with filtering
- GET    /api/v1/transactions/{id}            - Get single transaction
- PUT    /api/v1/transactions/{id}            - Update transaction
- DELETE /api/v1/transactions/{id}            - Delete transaction
- GET    /api/v1/transactions/accounts        - List distinct accounts
- GET    /api/v1/transactions/categories      - List distinct categories

Architecture Notes:
- Accounts and categories are labels (strings), not relational entities
- Entity registry pattern: create entity first, then transaction
- ISO 8601 timestamps for all date/time fields
- Parameterized queries to prevent SQL injection
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from .schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from ...exceptions import ResourceNotFound, ValidationError as MGValidationError
from ...utils import isodatetime
from ...db import get_core
from ..validation import validate_request


# Create Blueprint
transactions_bp = Blueprint('transactions', __name__)


def _row_to_transaction_response(row) -> dict:
    """
    Convert a database row from transactions_view to TransactionResponse dict.

    Args:
        row: SQLite Row object from transactions_view

    Returns:
        Dictionary matching TransactionResponse schema
    """
    return {
        "id": row["id"],
        "amount": row["amount"],
        "currency": row["currency"],
        "transaction_date": row["transaction_date"],
        "description": row["description"],
        "account": row["account"],
        "category": row["category"],
        "notes": row["notes"],
        "author": row["author"],
        "recurrence_id": row["recurrence_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "superseded_by": row["superseded_by"],
        "superseded_at": row["superseded_at"],
        "group_id": row["group_id"],
        "derived_from": row["derived_from"],
    }


@transactions_bp.post("")
@validate_request
def create_transaction(data: TransactionCreate):
    """
    Create a new transaction.

    Request Body (TransactionCreate):
        - amount: float (required)
        - currency: str (default: "SGD")
        - transaction_date: date (ISO 8601 YYYY-MM-DD, required)
        - description: str (default: "")
        - account: str (required)
        - category: str | None (default: None)
        - notes: str | None (default: None)

    Returns:
        201: TransactionResponse with created transaction
        400: Validation error
    """
    # ============================================================================
    # NEW: Core API Implementation with @validate_request decorator
    # ============================================================================
    # Use atomic transaction for coordinated entity + transaction creation
    with get_core(atomic=True) as core:
        transaction_id = core.transaction.create(
            amount=data.amount,
            transaction_date=data.transaction_date,
            description=data.description,
            account=data.account,
            category=data.category,
            notes=data.notes
        )
    # Context commits atomically - both entity and transaction created together

    # Fetch created transaction with fresh Core (connection closed after atomic block)
    core = get_core()
    row = core.transaction.get_by_id(transaction_id)

    return jsonify(_row_to_transaction_response(row)), 201

    # ============================================================================
    # LEGACY: Old implementation (kept for reference during migration)
    # ============================================================================
    # db = get_db()
    # try:
    #     data = TransactionCreate(**request.json)
    # except ValidationError as e:
    #     raise MGValidationError("Invalid request data", {"errors": e.errors()})
    #
    # entity_id = uid.generate_uuid()
    # create_entity(db, "transactions", entity_id)
    #
    # transaction_date_str = isodatetime.to_datestring(data.transaction_date)
    #
    # db.execute(
    #     """INSERT INTO transactions (
    #         id, amount, currency, transaction_date, description,
    #         account, category, author, notes
    #     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    #     (
    #         entity_id,
    #         data.amount,
    #         data.currency,
    #         transaction_date_str,
    #         data.description,
    #         data.account,
    #         data.category,
    #         "system",
    #         data.notes,
    #     )
    # )
    # db.commit()
    #
    # row = db.execute(
    #     "SELECT * FROM transactions_view WHERE id = ?",
    #     (entity_id,)
    # ).fetchone()
    #
    # return jsonify(_row_to_transaction_response(row)), 201


@transactions_bp.get("/<transaction_id>")
def get_transaction(transaction_id: str):
    """
    Get a single transaction by ID.

    Args:
        transaction_id: UUID of the transaction

    Returns:
        200: TransactionResponse
        404: Transaction not found
    """
    core = get_core()
    row = core.transaction.get_by_id(transaction_id)

    return jsonify(_row_to_transaction_response(row))


@transactions_bp.get("")
def list_transactions():
    """
    List transactions with optional filtering.

    Query Parameters:
        - start_date: ISO 8601 date (YYYY-MM-DD) - Filter from this date
        - end_date: ISO 8601 date (YYYY-MM-DD) - Filter until this date
        - account: str - Filter by account label
        - category: str - Filter by category label
        - include_superseded: bool - Include superseded transactions (default: false)
        - limit: int - Maximum results to return (default: 100)
        - offset: int - Number of results to skip (default: 0)

    Returns:
        200: Array of TransactionResponse objects
    """
    # Parse query parameters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    account = request.args.get("account")
    category = request.args.get("category")
    include_superseded = request.args.get("include_superseded", "false").lower() == "true"
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    filters = {
        "account": account,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "include_superseded": include_superseded
    }

    core = get_core()
    rows = core.transaction.list(filters, limit=limit, offset=offset)

    return jsonify([_row_to_transaction_response(row) for row in rows])


@transactions_bp.put("/<transaction_id>")
@validate_request
def update_transaction(transaction_id: str, data: TransactionUpdate):
    """
    Update a transaction.

    Only provided fields are updated (partial update).

    Args:
        transaction_id: UUID of the transaction

    Request Body (TransactionUpdate):
        All fields optional:
        - amount: float | None
        - currency: str | None
        - transaction_date: date | None
        - description: str | None
        - account: str | None
        - category: str | None
        - notes: str | None

    Returns:
        200: TransactionResponse with updated transaction
        404: Transaction not found
        400: Validation error
    """
    core = get_core()

    # Verify transaction exists
    core.transaction.get_by_id(transaction_id)

    # Build update data from only provided fields
    update_data = data.model_dump(exclude_unset=True)

    if update_data:
        core.transaction.update(transaction_id, update_data)

    # Fetch updated transaction
    row = core.transaction.get_by_id(transaction_id)

    return jsonify(_row_to_transaction_response(row))


@transactions_bp.delete("/<transaction_id>")
def delete_transaction(transaction_id: str):
    """
    Delete a transaction (soft delete via superseding).

    Creates a tombstone entity and marks the original as superseded.

    Args:
        transaction_id: UUID of the transaction

    Returns:
        204: No content (successful deletion)
        404: Transaction not found
    """
    with get_core(atomic=True) as core:
        # Verify transaction exists
        core.transaction.get_by_id(transaction_id)

        # Create tombstone entity
        tombstone_id = core.entity.create("transactions")

        # Mark original as superseded
        core.entity.supersede(transaction_id, tombstone_id)

    return "", 204


@transactions_bp.get("/accounts")
def list_accounts():
    """
    List distinct account labels.

    Useful for UI autocomplete/dropdowns.
    Accounts are simple string labels, not entities.

    Returns:
        200: Array of account label strings
    """
    core = get_core()
    rows = core._conn.execute(
        "SELECT DISTINCT account FROM transactions WHERE account IS NOT NULL ORDER BY account"
    ).fetchall()

    return jsonify([row["account"] for row in rows])


@transactions_bp.get("/categories")
def list_categories():
    """
    List distinct category labels.

    Useful for UI autocomplete/dropdowns.
    Categories are simple string labels, not entities.

    Returns:
        200: Array of category label strings
    """
    core = get_core()
    rows = core._conn.execute(
        "SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL ORDER BY category"
    ).fetchall()

    return jsonify([row["category"] for row in rows])
