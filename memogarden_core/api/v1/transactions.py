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

from ...schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from ...exceptions import ResourceNotFound, ValidationError as MGValidationError
from ...utils import isodatetime
from ...db import get_core, get_db


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
def create_transaction():
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
    # NEW: Core API Implementation
    # ============================================================================
    try:
        # Validate request body
        data = TransactionCreate(**request.json)
    except ValidationError as e:
        raise MGValidationError("Invalid request data", {"errors": e.errors()})

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


@transactions_bp.route("<transaction_id>", methods=["GET"])
def get_transaction(transaction_id: str):
    """
    Get a single transaction by ID.

    Args:
        transaction_id: UUID of the transaction

    Returns:
        200: TransactionResponse
        404: Transaction not found
    """
    db = get_db()

    row = db.execute(
        "SELECT * FROM transactions_view WHERE id = ?",
        (transaction_id,)
    ).fetchone()

    if not row:
        raise ResourceNotFound(
            f"Transaction not found",
            {"transaction_id": transaction_id}
        )

    return jsonify(_row_to_transaction_response(row))


@transactions_bp.route("", methods=["GET"])
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
    db = get_db()

    # Parse query parameters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    account = request.args.get("account")
    category = request.args.get("category")
    include_superseded = request.args.get("include_superseded", "false").lower() == "true"
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    # Build dynamic WHERE clause
    conditions = []
    params = []

    if start_date:
        conditions.append("t.transaction_date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("t.transaction_date <= ?")
        params.append(end_date)

    if account:
        conditions.append("t.account = ?")
        params.append(account)

    if category:
        conditions.append("t.category = ?")
        params.append(category)

    if not include_superseded:
        conditions.append("e.superseded_by IS NULL")

    # Build base query
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT t.*,
               e.created_at, e.updated_at, e.superseded_by, e.superseded_at,
               e.group_id, e.derived_from
        FROM transactions t
        JOIN entity e ON t.id = e.id
        WHERE {where_clause}
        ORDER BY t.transaction_date DESC, e.created_at DESC
        LIMIT ? OFFSET ?
    """

    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()

    return jsonify([
        {
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
        for row in rows
    ])


@transactions_bp.route("<transaction_id>", methods=["PUT"])
def update_transaction(transaction_id: str):
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
    db = get_db()

    # Check if transaction exists
    row = db.execute(
        "SELECT * FROM transactions_view WHERE id = ?",
        (transaction_id,)
    ).fetchone()

    if not row:
        raise ResourceNotFound(
            f"Transaction not found",
            {"transaction_id": transaction_id}
        )

    try:
        # Validate request body (all fields optional)
        data = TransactionUpdate(**request.json)
    except ValidationError as e:
        raise MGValidationError("Invalid request data", {"errors": e.errors()})

    # Build UPDATE dynamically based on provided fields
    update_fields = []
    params = []

    if data.amount is not None:
        update_fields.append("amount = ?")
        params.append(data.amount)

    if data.currency is not None:
        update_fields.append("currency = ?")
        params.append(data.currency)

    if data.transaction_date is not None:
        update_fields.append("transaction_date = ?")
        params.append(isodatetime.to_datestring(data.transaction_date))

    if data.description is not None:
        update_fields.append("description = ?")
        params.append(data.description)

    if data.account is not None:
        update_fields.append("account = ?")
        params.append(data.account)

    if data.category is not None:
        update_fields.append("category = ?")
        params.append(data.category)

    if data.notes is not None:
        update_fields.append("notes = ?")
        params.append(data.notes)

    if update_fields:
        # Add transaction_id to params
        params.append(transaction_id)

        # Update transaction
        db.execute(
            f"UPDATE transactions SET {', '.join(update_fields)} WHERE id = ?",
            params
        )

        # Update entity registry updated_at
        now = isodatetime.now()
        db.execute(
            "UPDATE entity SET updated_at = ? WHERE id = ?",
            (now, transaction_id)
        )

        db.commit()

    # Fetch updated transaction
    row = db.execute(
        "SELECT * FROM transactions_view WHERE id = ?",
        (transaction_id,)
    ).fetchone()

    return jsonify(_row_to_transaction_response(row))


@transactions_bp.route("<transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id: str):
    """
    Delete a transaction.

    Hard delete - removes transaction from database.
    CASCADE deletes from entity registry automatically.

    Args:
        transaction_id: UUID of the transaction

    Returns:
        204: No content (successful deletion)
        404: Transaction not found
    """
    db = get_db()

    # Check if transaction exists
    row = db.execute(
        "SELECT id FROM transactions WHERE id = ?",
        (transaction_id,)
    ).fetchone()

    if not row:
        raise ResourceNotFound(
            f"Transaction not found",
            {"transaction_id": transaction_id}
        )

    # Delete transaction (entity registry CASCADE deletes automatically)
    db.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,)
    )
    db.commit()

    return "", 204


@transactions_bp.route("accounts", methods=["GET"])
def list_accounts():
    """
    List distinct account labels.

    Useful for UI autocomplete/dropdowns.
    Accounts are simple string labels, not entities.

    Returns:
        200: Array of account label strings
    """
    db = get_db()

    rows = db.execute(
        "SELECT DISTINCT account FROM transactions WHERE account IS NOT NULL ORDER BY account"
    ).fetchall()

    return jsonify([row["account"] for row in rows])


@transactions_bp.route("categories", methods=["GET"])
def list_categories():
    """
    List distinct category labels.

    Useful for UI autocomplete/dropdowns.
    Categories are simple string labels, not entities.

    Returns:
        200: Array of category label strings
    """
    db = get_db()

    rows = db.execute(
        "SELECT DISTINCT category FROM transactions WHERE category IS NOT NULL ORDER BY category"
    ).fetchall()

    return jsonify([row["category"] for row in rows])
