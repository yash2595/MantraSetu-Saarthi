"""Unique Identifier utility module.

Provides functions for generating UUIDs and URL-safe short IDs.
"""

import secrets
import string
import uuid

# URL-safe alphanumeric character set for short ID generation
_URL_SAFE_CHARACTERS = string.ascii_letters + string.digits


def generate_uuid() -> str:
    """Generate a random UUIDv4 string.

    Returns:
        str: Lowercase 36-character UUID string (e.g., '123e4567-e89b-12d3-a456-426614174000').
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 12) -> str:
    """Generate a URL-safe cryptographically secure random short identifier.

    Args:
        length: The desired character length of the ID (default 12).

    Returns:
        str: URL-safe random string identifier of specified length.

    Raises:
        ValueError: If length is less than 1.
    """
    if length < 1:
        raise ValueError("ID length must be at least 1.")

    return "".join(secrets.choice(_URL_SAFE_CHARACTERS) for _ in range(length))
