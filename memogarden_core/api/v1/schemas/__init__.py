"""Pydantic schemas for API validation.

Transaction schemas are defined here for API v1.
Auth schemas are imported from the auth module for use in API endpoints.
"""

from .transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

# Re-export auth schemas for convenience in API endpoints
from memogarden_core.auth.schemas import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    APIKeyBase,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    TokenPayload,
    TokenResponse,
    AdminRegistrationResponse,
)

__all__ = [
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
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
