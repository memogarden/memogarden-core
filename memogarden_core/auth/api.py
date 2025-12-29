"""Authentication API endpoints for MemoGarden Core.

These endpoints handle user authentication and return JSON responses:
- Admin registration (localhost only, one-time)
- User login and logout
- User profile retrieval
- API key management

All endpoints return JSON responses. Admin registration is only accessible
from localhost and only when no users exist in the database.
"""

import logging
import sqlite3

from flask import Blueprint, jsonify, request

from ..api.validation import validate_request
from ..db import get_core
from ..exceptions import AuthenticationError
from . import api_keys, service, token
from .schemas import AdminRegistrationResponse, APIKeyCreate, TokenResponse, UserCreate, UserLogin

logger = logging.getLogger(__name__)


# Create blueprint
auth_bp = Blueprint("auth", __name__)


# ============================================================================
# Admin Registration (localhost only, one-time)
# ============================================================================


def _is_localhost_request() -> bool:
    """
    Check if the request is from localhost.

    Returns True if the remote address is localhost (127.0.0.1, ::1, or 'localhost').
    Can be bypassed via config.bypass_localhost_check for testing.
    """
    from ..config import settings

    if settings.bypass_localhost_check:
        return False

    remote_addr = request.remote_addr or ""
    return remote_addr in {"127.0.0.1", "::1", "localhost"}


@auth_bp.route("/admin/register", methods=["POST"])
@validate_request
def admin_register(data: UserCreate):
    """
    Create admin account (localhost only, one-time).

    This endpoint is only accessible:
    1. From localhost (127.0.0.1, ::1)
    2. When no users exist in the database

    Args:
        data: User creation data with username and password

    Returns:
        Admin registration response with created user

    Raises:
        AuthenticationError: If not localhost or admin already exists
        ValidationError: If request data is invalid

    Example request:
    ```json
    {
        "username": "admin",
        "password": "SecurePass123"
    }
    ```

    Example response:
    ```json
    {
        "message": "Admin account created successfully",
        "user": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "admin",
            "is_admin": true,
            "created_at": "2025-12-29T10:30:00Z"
        }
    }
    ```
    """
    # Check localhost access
    if not _is_localhost_request():
        logger.warning(f"Admin registration attempt from non-localhost: {request.remote_addr}")
        raise AuthenticationError(
            "Admin registration is only accessible from localhost",
            {"remote_addr": request.remote_addr}
        )

    core = get_core()
    try:
        # Check if admin already exists
        if service.has_admin_user(core._conn):
            logger.warning("Admin registration attempted when admin already exists")
            raise AuthenticationError(
                "Admin account already exists. Registration is disabled."
            )

        # Create admin user
        user = service.create_user(core._conn, data, is_admin=True)
        core._conn.commit()

        logger.info(f"Admin account created: {user.username}")

        return jsonify(
            AdminRegistrationResponse(
                message="Admin account created successfully",
                user=user
            ).model_dump()
        ), 201

    except sqlite3.IntegrityError:
        logger.warning(f"Admin registration failed (username exists): {data.username}")
        raise AuthenticationError(
            "Username already exists",
            {"username": data.username}
        )
    # Connection closes automatically via __del__


# ============================================================================
# Authentication Endpoints
# ============================================================================


@auth_bp.route("/auth/login", methods=["POST"])
@validate_request
def login(data: UserLogin):
    """
    Authenticate user and return JWT token.

    Accepts both JSON and form data (for HTML forms).

    Args:
        data: Login credentials with username and password

    Returns:
        Token response with JWT access token and user info

    Raises:
        AuthenticationError: If credentials are invalid

    Example request (JSON):
    ```json
    {
        "username": "admin",
        "password": "SecurePass123"
    }
    ```

    Example request (form data):
    ```
    username=admin&password=SecurePass123
    ```

    Example response:
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "user": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "admin",
            "is_admin": true,
            "created_at": "2025-12-29T10:30:00Z"
        }
    }
    ```
    """
    core = get_core()
    # Verify credentials
    user = service.verify_credentials(core._conn, data.username, data.password)
    if user is None:
        logger.warning(f"Failed login attempt for username: {data.username}")
        raise AuthenticationError(
            "Invalid username or password",
            {"username": data.username}
        )

    # Generate JWT token
    access_token = token.generate_access_token(user)

    logger.info(f"Successful login: {user.username}")

    return jsonify(
        TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        ).model_dump()
    ), 200
    # Connection closes automatically via __del__


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    """
    Logout user (no-op for MVP).

    In the current MVP, JWT tokens are self-validating and stateless.
    The client should simply discard the token. This endpoint exists
    for API compatibility and future token blacklist support.

    Returns:
        Success message

    Example response:
    ```json
    {
        "message": "Logged out successfully"
    }
    ```
    """
    # For MVP: tokens are stateless, just return success
    # Future: implement token blacklist if needed
    return jsonify({"message": "Logged out successfully"}), 200


# ============================================================================
# User Profile Endpoints
# ============================================================================


@auth_bp.route("/auth/me", methods=["GET"])
def get_current_user():
    """
    Get current user info from JWT token.

    This endpoint requires authentication via the Authorization header:
    Authorization: Bearer <token>

    Returns:
        User info for authenticated user

    Raises:
        AuthenticationError: If token is missing or invalid

    Example request:
    ```
    GET /auth/me
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```

    Example response:
    ```json
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "admin",
        "is_admin": true,
        "created_at": "2025-12-29T10:30:00Z"
    }
    ```
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        raise AuthenticationError(
            "Missing authorization header",
            {"expected": "Authorization: Bearer <token>"}
        )

    # Parse Bearer token
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid authorization header format",
            {"expected": "Authorization: Bearer <token>"}
        )

    jwt_token = parts[1]

    # Validate token
    try:
        payload = token.validate_access_token(jwt_token)
    except Exception as e:
        logger.warning(f"Invalid token on /auth/me: {e}")
        raise AuthenticationError(
            "Invalid or expired token",
            {"token": jwt_token[:20] + "..."}  # Log prefix only
        )

    # Get user from database
    core = get_core()
    user = service.get_user_by_id(core._conn, payload.sub)
    if user is None:
        raise AuthenticationError(
            "User not found",
            {"user_id": payload.sub}
        )

    return jsonify(user.model_dump()), 200
    # Connection closes automatically via __del__


# ============================================================================
# API Key Management Endpoints
# ============================================================================


@auth_bp.route("/api-keys/", methods=["GET"])
def list_api_keys():
    """
    List all API keys for the authenticated user.

    Requires authentication via JWT token.
    Full API keys are never shown in the list (only prefix).

    Returns:
        List of API key responses (without full keys)

    Raises:
        AuthenticationError: If token is missing or invalid

    Example request:
    ```
    GET /api-keys/
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```

    Example response:
    ```json
    [
        {
            "id": "660e8400-e29b-41d4-a716-446655440000",
            "name": "claude-code",
            "prefix": "mg_sk_agent_",
            "expires_at": null,
            "created_at": "2025-12-29T10:30:00Z",
            "last_seen": "2025-12-29T15:45:00Z",
            "revoked_at": null
        }
    ]
    ```
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        raise AuthenticationError(
            "Missing authorization header",
            {"expected": "Authorization: Bearer <token>"}
        )

    # Parse Bearer token
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid authorization header format",
            {"expected": "Authorization: Bearer <token>"}
        )

    jwt_token = parts[1]

    # Validate token and get user ID
    try:
        payload = token.validate_access_token(jwt_token)
    except Exception as e:
        logger.warning(f"Invalid token on /api-keys/: {e}")
        raise AuthenticationError(
            "Invalid or expired token",
            {"token": jwt_token[:20] + "..."}
        )

    # List API keys for user
    core = get_core()
    api_keys_list = api_keys.list_api_keys(core._conn, payload.sub)

    return jsonify([key.model_dump() for key in api_keys_list]), 200
    # Connection closes automatically via __del__


@auth_bp.route("/api-keys/", methods=["POST"])
@validate_request
def create_api_key(data: APIKeyCreate):
    """
    Create a new API key for the authenticated user.

    Requires authentication via JWT token.
    The full API key is only shown once in the response.

    Args:
        data: API key creation data with name and optional expires_at

    Returns:
        Created API key response with full key (only shown once)

    Raises:
        AuthenticationError: If token is missing or invalid

    Example request:
    ```json
    {
        "name": "claude-code",
        "expires_at": "2026-12-31T23:59:59Z"
    }
    ```

    Example response:
    ```json
    {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "name": "claude-code",
        "key": "mg_sk_agent_9a2b8c7d...",
        "prefix": "mg_sk_agent_",
        "expires_at": "2026-12-31T23:59:59Z",
        "created_at": "2025-12-29T10:30:00Z",
        "last_seen": null,
        "revoked_at": null
    }
    ```
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        raise AuthenticationError(
            "Missing authorization header",
            {"expected": "Authorization: Bearer <token>"}
        )

    # Parse Bearer token
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid authorization header format",
            {"expected": "Authorization: Bearer <token>"}
        )

    jwt_token = parts[1]

    # Validate token and get user ID
    try:
        payload = token.validate_access_token(jwt_token)
    except Exception as e:
        logger.warning(f"Invalid token on /api-keys/: {e}")
        raise AuthenticationError(
            "Invalid or expired token",
            {"token": jwt_token[:20] + "..."}
        )

    # Create API key
    core = get_core()
    api_key = api_keys.create_api_key(core._conn, payload.sub, data)
    core._conn.commit()

    logger.info(f"API key created: {api_key.name} for user {payload.sub}")

    return jsonify(api_key.model_dump()), 201


@auth_bp.route("/api-keys/<api_key_id>", methods=["DELETE"])
def revoke_api_key(api_key_id: str):
    """
    Revoke an API key for the authenticated user (soft delete).

    Requires authentication via JWT token.
    Sets the revoked_at timestamp to deactivate the key.

    Args:
        api_key_id: API key UUID to revoke

    Returns:
        Success message

    Raises:
        AuthenticationError: If token is missing or invalid
        ResourceNotFound: If API key doesn't exist or doesn't belong to user

    Example request:
    ```
    DELETE /api-keys/660e8400-e29b-41d4-a716-446655440000
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```

    Example response:
    ```json
    {
        "message": "API key revoked successfully"
    }
    ```
    """
    from ..exceptions import ResourceNotFound

    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        raise AuthenticationError(
            "Missing authorization header",
            {"expected": "Authorization: Bearer <token>"}
        )

    # Parse Bearer token
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(
            "Invalid authorization header format",
            {"expected": "Authorization: Bearer <token>"}
        )

    jwt_token = parts[1]

    # Validate token and get user ID
    try:
        payload = token.validate_access_token(jwt_token)
    except Exception as e:
        logger.warning(f"Invalid token on /api-keys/: {e}")
        raise AuthenticationError(
            "Invalid or expired token",
            {"token": jwt_token[:20] + "..."}
        )

    # Revoke API key
    core = get_core()
    success = api_keys.revoke_api_key(core._conn, api_key_id, payload.sub)
    core._conn.commit()

    if not success:
        raise ResourceNotFound(
            "API key not found",
            {"api_key_id": api_key_id}
        )

    logger.info(f"API key revoked: {api_key_id} by user {payload.sub}")

    return jsonify({"message": "API key revoked successfully"}), 200
    # Connection closes automatically via __del__
