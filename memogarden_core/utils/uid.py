"""UUID generation utilities.

This module centralizes all UUID generation. This is the ONLY module that
should import uuid4. All other code should use uid.generate_uuid().
"""

from uuid import uuid4


def generate_uuid() -> str:
    """Generate a random UUID v4 as a string."""
    return str(uuid4())
