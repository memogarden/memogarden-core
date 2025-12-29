"""Authentication decorators for protected endpoints.

This module provides decorators for enforcing security constraints on endpoints:
- @localhost_only - Restricts access to localhost only
- @first_time_only - Restricts access to first-time setup (no admin exists)

These decorators follow the project's pattern of declarative endpoint security
and can be composed together for multiple constraints.
"""

import logging
from functools import wraps

from flask import request

from ..db import get_core
from ..exceptions import AuthenticationError
from . import service

logger = logging.getLogger(__name__)


# ============================================================================
# Localhost-Only Decorator
# ============================================================================


def localhost_only(f):
    """
    Decorator to restrict endpoint access to localhost only.

    Checks that the request originates from localhost (127.0.0.1, ::1).
    When config.bypass_localhost_check is True, treats requests as non-localhost.

    Raises:
        AuthenticationError: If request is not from localhost

    Example:
    ```python
    @localhost_only
    def sensitive_setup():
        # Only accessible from localhost
        ...
    ```
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        from ..config import settings

        # Check remote address
        remote_addr = request.remote_addr or ""

        # When bypass is enabled, treat as non-localhost (for testing)
        if settings.bypass_localhost_check:
            remote_addr = "192.168.1.100"  # Simulate non-localhost

        if remote_addr not in {"127.0.0.1", "::1", "localhost"}:
            logger.warning(f"Protected endpoint accessed from non-localhost: {remote_addr}")
            raise AuthenticationError(
                "This endpoint is only accessible from localhost",
                {"remote_addr": remote_addr}
            )

        return f(*args, **kwargs)

    return wrapper


# ============================================================================
# First-Time-Only Decorator
# ============================================================================


def first_time_only(f):
    """
    Decorator to restrict endpoint access to first-time setup only.

    Checks that no admin user exists in the database.
    Used for one-time setup operations like admin registration.

    Raises:
        AuthenticationError: If an admin user already exists

    Example:
    ```python
    @first_time_only
    def admin_registration():
        # Only accessible when no admin exists
        ...
    ```
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        core = get_core()

        # Check if admin already exists
        if service.has_admin_user(core._conn):
            logger.warning("First-time endpoint accessed after setup completed")
            raise AuthenticationError(
                "Setup has already been completed. This endpoint is disabled."
            )

        return f(*args, **kwargs)

    return wrapper
