"""Idempotency key handling.

SIBS' public documentation does not (at the time of writing) clearly document a
dedicated idempotency request header. To avoid sending undocumented headers, PySIBS
keeps idempotency support behind a single switch:

* ``IDEMPOTENCY_HEADER`` is ``None`` by default, which means an ``idempotency_key``
  passed by the caller is validated and kept as metadata but **not** sent on the wire.
* If/when SIBS confirms a header name, set ``IDEMPOTENCY_HEADER`` to that name (or pass
  ``idempotency_header`` to the client) and the key will be sent automatically.

This keeps the public API stable (callers can always pass ``idempotency_key``) while
guaranteeing the library never invents a header.
"""

from __future__ import annotations

from .exceptions import SIBSValidationError

__all__ = ["IDEMPOTENCY_HEADER", "build_idempotency_headers", "validate_idempotency_key"]

# Default: do not send any idempotency header (not documented by SIBS).
IDEMPOTENCY_HEADER: str | None = None


def validate_idempotency_key(key: str) -> str:
    """Validate a caller-supplied idempotency key."""
    if not isinstance(key, str) or not key.strip():
        raise SIBSValidationError("idempotency_key must be a non-empty string.")
    stripped = key.strip()
    if len(stripped) > 255:
        raise SIBSValidationError("idempotency_key must be at most 255 characters.")
    return stripped


def build_idempotency_headers(
    key: str | None, header_name: str | None = IDEMPOTENCY_HEADER
) -> dict[str, str]:
    """Return the headers to attach for a given idempotency key.

    Returns an empty mapping when no key is provided or when no header name is
    configured (the default), so nothing undocumented is ever sent.
    """
    if key is None:
        return {}
    validated = validate_idempotency_key(key)
    if not header_name:
        return {}
    return {header_name: validated}
