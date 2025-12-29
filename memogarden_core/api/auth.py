"""Authentication endpoints for MemoGarden Core.

These endpoints handle user authentication:
- Admin registration (localhost only, one-time)
- User login and logout
- User profile retrieval

All endpoints return JSON responses. Admin registration is only accessible
from localhost and only when no users exist in the database.
"""

import logging
from flask import Blueprint, jsonify, request, render_template_string
import sqlite3

from ..db import get_core
from ..auth import service, token
from ..auth.schemas import UserCreate, UserLogin, TokenResponse, AdminRegistrationResponse
from ..api.validation import validate_request
from ..exceptions import AuthenticationError

logger = logging.getLogger(__name__)


# Create blueprint
auth_bp = Blueprint("auth", __name__)


# ============================================================================
# Admin Registration (localhost only, one-time)
# ============================================================================

ADMIN_REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MemoGarden - Admin Setup</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 500px;
            margin: 50px auto;
            padding: 20px;
        }
        h1 { color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover { background: #0056b3; }
        .error {
            color: #dc3545;
            padding: 10px;
            background: #f8d7da;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .info {
            color: #004085;
            padding: 10px;
            background: #cce5ff;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .hint {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <h1>MemoGarden Admin Setup</h1>

    {% if message %}
    <div class="info">{{ message }}</div>
    {% endif %}

    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}

    <form method="POST" action="/admin/register">
        <div class="form-group">
            <label for="username">Username</label>
            <input
                type="text"
                id="username"
                name="username"
                required
                pattern="[A-Za-z0-9_-]+"
                title="Letters, numbers, underscores, and hyphens only"
                autocomplete="username"
            />
            <div class="hint">Letters, numbers, underscores, and hyphens only</div>
        </div>

        <div class="form-group">
            <label for="password">Password</label>
            <input
                type="password"
                id="password"
                name="password"
                required
                minlength="8"
                autocomplete="new-password"
            />
            <div class="hint">Minimum 8 characters, must contain at least one letter and one digit</div>
        </div>

        <button type="submit">Create Admin Account</button>
    </form>
</body>
</html>
"""


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


@auth_bp.route("/admin/register", methods=["GET"])
def admin_register_page():
    """
    Display admin registration page (localhost only).

    This page is only accessible:
    1. From localhost (127.0.0.1, ::1)
    2. When no users exist in the database

    Returns:
        HTML page with admin registration form

    Error Responses:
        403: If not localhost or admin already exists
    """
    # Check localhost access
    if not _is_localhost_request():
        logger.warning(f"Admin registration attempt from non-localhost: {request.remote_addr}")
        return jsonify({
            "error": {
                "type": "Forbidden",
                "message": "Admin registration is only accessible from localhost"
            }
        }), 403

    # Check if any users exist
    core = get_core()
    try:
        if service.has_admin_user(core._conn):
            logger.warning("Admin registration attempted when admin already exists")
            return render_template_string(
                ADMIN_REGISTER_HTML,
                error="Admin account already exists. Registration is disabled.",
                message=None
            )

        return render_template_string(ADMIN_REGISTER_HTML, error=None, message=None)
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return jsonify({
            "error": {
                "type": "InternalServerError",
                "message": "Failed to check admin status"
            }
        }), 500
    # Connection closes automatically via __del__


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

    except sqlite3.IntegrityError as e:
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
