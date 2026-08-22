"""API key generation and hashing utilities.

Author: Farruh
"""

from __future__ import annotations

import hashlib
import secrets


def generate_api_key(prefix: str = "sk") -> str:
    """Generate a cryptographically secure API key.

    Args:
        prefix: Short human-readable prefix (e.g. ``"sk"`` for secret key).

    Returns:
        A URL-safe base64-encoded key string, e.g. ``"sk-abc123..."``.
    """
    return f"{prefix}-{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """Return the SHA-256 fingerprint of a raw API key.

    Only the fingerprint is stored in the database; the raw key is
    never persisted after the initial creation response.

    Args:
        raw_key: The plaintext API key.

    Returns:
        A 64-character hex digest.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
