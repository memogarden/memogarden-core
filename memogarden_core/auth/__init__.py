"""Authentication module for MemoGarden Core.

This module provides authentication and authorization functionality:
- Schema validation for auth operations
- JWT token generation and validation
- Password hashing and verification
- Authentication middleware for protected endpoints
- User and API key management

Auth endpoints (top-level routes, not under /api/v1/):
- POST /admin/register - Create admin account (localhost only)
- POST /auth/login - Authenticate and return JWT token
- POST /auth/logout - Revoke current token
- GET /auth/me - Get current user info
- GET /api-keys/ - List API keys for current user
- POST /api-keys/ - Create new API key
- DELETE /api-keys/:id - Revoke API key
"""

from . import schemas, token

__all__ = ["schemas", "token"]
