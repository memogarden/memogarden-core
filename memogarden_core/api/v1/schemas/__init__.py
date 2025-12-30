"""Pydantic schemas for API validation.

Transaction and recurrence schemas are defined here for API v1.
Auth schemas are imported from the auth module for use in API endpoints.
"""

# Re-export auth schemas for convenience in API endpoints
from memogarden_core.auth.schemas import (
    AdminRegistrationResponse,
    APIKeyBase,
    APIKeyCreate,
    APIKeyListResponse,
    APIKeyResponse,
    TokenPayload,
    TokenResponse,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
)

from .recurrence import (
    RecurrenceBase,
    RecurrenceCreate,
    RecurrenceResponse,
    RecurrenceUpdate,
)
from .transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

__all__ = [
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "RecurrenceBase",
    "RecurrenceCreate",
    "RecurrenceUpdate",
    "RecurrenceResponse",
    # Auth schemas (re-exported from memogarden_core.auth.schemas)
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "APIKeyBase",
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyListResponse",
    "TokenPayload",
    "TokenResponse",
    "AdminRegistrationResponse",
]
