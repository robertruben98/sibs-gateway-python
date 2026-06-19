"""Lightweight input validators used by the client before calling SIBS.

These validators perform cheap, defensive checks so obviously-wrong input fails fast
with a clear :class:`SIBSValidationError` instead of producing a confusing API error.
They are deliberately conservative: they catch empty/blank values and gross format
problems without trying to fully validate SIBS' business rules.
"""

from __future__ import annotations

import re

from .exceptions import SIBSValidationError

__all__ = [
    "validate_currency",
    "validate_merchant_transaction_id",
    "validate_url",
    "validate_payment_id",
    "validate_terminal_id",
    "validate_mbway_phone",
]

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
# SIBS MB WAY phone format: "<countryCode>#<number>", e.g. "351#911234567".
_MBWAY_PHONE_RE = re.compile(r"^\d{1,4}#\d{6,15}$")


def _require_non_empty(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise SIBSValidationError(f"{field} must be a string; got {type(value).__name__}.")
    stripped = value.strip()
    if not stripped:
        raise SIBSValidationError(f"{field} must not be empty.")
    return stripped


def validate_currency(currency: str) -> str:
    """Validate an ISO-4217-style 3-letter currency code, returning it upper-cased."""
    stripped = _require_non_empty(currency, "currency").upper()
    if not _CURRENCY_RE.match(stripped):
        raise SIBSValidationError(
            f"currency must be a 3-letter ISO code (e.g. 'EUR'); got {currency!r}."
        )
    return stripped


def validate_merchant_transaction_id(value: str) -> str:
    """Validate a merchant transaction id (must be non-empty)."""
    return _require_non_empty(value, "merchant_transaction_id")


def validate_payment_id(value: str) -> str:
    """Validate a SIBS payment / transaction id (must be non-empty)."""
    return _require_non_empty(value, "payment_id")


def validate_terminal_id(value: str) -> str:
    """Validate a terminal id (must be non-empty)."""
    return _require_non_empty(str(value) if value is not None else "", "terminal_id")


def validate_mbway_phone(value: str) -> str:
    """Validate an MB WAY phone in SIBS' ``"<countryCode>#<number>"`` format.

    Example: ``"351#911234567"``. A plain national number is rejected because SIBS
    requires the country-code prefix and ``#`` separator.
    """
    stripped = _require_non_empty(value, "customer_phone")
    if not _MBWAY_PHONE_RE.match(stripped):
        raise SIBSValidationError(
            "customer_phone must look like '<countryCode>#<number>' (e.g. '351#911234567'); "
            f"got {value!r}."
        )
    return stripped


def validate_url(value: str, *, require_https: bool = True) -> str:
    """Validate a URL.

    When ``require_https`` is true (the default), the URL must start with
    ``https://``. Callers operating against the sandbox can relax this.
    """
    stripped = _require_non_empty(value, "url")
    if require_https:
        if not stripped.lower().startswith("https://"):
            raise SIBSValidationError(f"URL must start with 'https://'; got {value!r}.")
    elif not re.match(r"^https?://", stripped, re.IGNORECASE):
        raise SIBSValidationError(f"URL must start with 'http(s)://'; got {value!r}.")
    return stripped
