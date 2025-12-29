"""API v1 endpoints for MemoGarden Core.

This module provides the ApiV1 blueprint that aggregates all v1 resources:
- Transactions
- Future: Accounts, Categories, Recurrences, Relations, Deltas

The ApiV1 blueprint is registered in main.py and provides a central point
for applying security decorators and middleware to all v1 endpoints.
"""

from flask import Blueprint

from . import transactions

# Create the ApiV1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Register transactions blueprint under ApiV1
# Note: transactions_bp has url_prefix="/transactions", so full path will be /api/v1/transactions
api_v1_bp.register_blueprint(transactions.transactions_bp)

__all__ = ["api_v1_bp"]
