"""Redaction helpers to keep sensitive data out of logs and error output.

PySIBS never logs request/response bodies or the ``Authorization`` header. When you do
need to log something that *might* contain cardholder data (e.g. an opaque card payload
you built), run it through :func:`redact` first.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["mask_pan", "redact", "SENSITIVE_KEYS"]

# Keys whose values must never be shown in full, matched case-insensitively as a
# substring (so e.g. "cardNumber", "card_number", "securityCode" all match).
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "number",
        "pan",
        "cardnumber",
        "card_number",
        "cvv",
        "cvv2",
        "cvc",
        "securitycode",
        "security_code",
        "card",
        "authorization",
        "token",
        "secret",
        "password",
        "apikey",
        "api_key",
        "transactionsignature",
        "transaction_signature",
    }
)

# A run of 12-19 digits (optionally split by single spaces/dashes) looks like a PAN.
# Anchored on digits at both ends so a trailing separator is not swallowed.
_PAN_RE = re.compile(r"\b\d(?:[ -]?\d){11,18}\b")
_MASK = "***REDACTED***"


def mask_pan(value: str) -> str:
    """Mask anything that looks like a card number, keeping the last 4 digits.

    ``"4111 1111 1111 1111"`` -> ``"************1111"``. Non-PAN text is returned
    unchanged.
    """

    def _replace(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < 12:
            return match.group(0)
        return "*" * (len(digits) - 4) + digits[-4:]

    return _PAN_RE.sub(_replace, value)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "").replace("_", "").lower()
    return any(s.replace("_", "") in normalized for s in SENSITIVE_KEYS)


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Return a copy of ``value`` with sensitive fields masked, safe for logging.

    Recurses into dicts/lists. Values under a sensitive key are fully redacted; free
    strings have PAN-like sequences masked. Never mutates the input.
    """
    if _depth > 12:
        return _MASK
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for key, val in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                out[key] = _MASK
            else:
                out[key] = redact(val, _depth=_depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v, _depth=_depth + 1) for v in value)
    if isinstance(value, str):
        return mask_pan(value)
    return value
