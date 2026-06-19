"""Normalized enumerations and status mapping.

SIBS returns a range of status strings and numeric status codes that differ between
products and endpoints. To give callers a stable surface, PySIBS maps those raw
values onto :class:`PaymentStatus`. The mapping is intentionally forgiving: any value
we do not recognise is mapped to :attr:`PaymentStatus.UNKNOWN` rather than raising,
so a new SIBS status can never break an integration. The untouched raw value is
always preserved on the response models via ``raw_status``.
"""

from __future__ import annotations

from enum import Enum

__all__ = [
    "PaymentStatus",
    "PaymentMethod",
    "TransactionType",
    "normalize_payment_status",
]


class PaymentStatus(str, Enum):
    """Normalized payment lifecycle states."""

    CREATED = "created"
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    DECLINED = "declined"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    EXPIRED = "expired"
    ERROR = "error"
    UNKNOWN = "unknown"


class PaymentMethod(str, Enum):
    """Payment methods supported by SIBS Gateway.

    The wire value for a MULTIBANCO reference payment is ``"REFERENCE"``. ``MULTIBANCO``
    is kept as a backwards-compatible alias of ``REFERENCE`` (same value).
    """

    CARD = "CARD"
    MBWAY = "MBWAY"
    REFERENCE = "REFERENCE"
    MULTIBANCO = "REFERENCE"  # alias of REFERENCE (deprecated name)


class TransactionType(str, Enum):
    """SIBS transaction types: a purchase captures immediately, an authorization holds
    the amount until a capture is performed."""

    PURCHASE = "PURS"
    AUTHORIZATION = "AUTH"

    @classmethod
    def coerce(cls, value: str | TransactionType) -> TransactionType:
        if isinstance(value, cls):
            return value
        token = str(value).strip().upper()
        # Accept both the wire codes (PURS/AUTH) and friendly names.
        aliases = {
            "PURS": cls.PURCHASE,
            "PURCHASE": cls.PURCHASE,
            "AUTH": cls.AUTHORIZATION,
            "AUTHORIZATION": cls.AUTHORIZATION,
            "AUTHORISATION": cls.AUTHORIZATION,
        }
        if token in aliases:
            return aliases[token]
        from .exceptions import SIBSValidationError

        raise SIBSValidationError(
            f"Invalid transaction_type {value!r}; expected one of: PURS, AUTH."
        )


# Mapping of known raw SIBS status tokens (lower-cased) to normalized statuses.
#
# NOTE: SIBS uses different vocabularies across endpoints/products. This table is a
# best-effort, conservative mapping and should be extended as the official behaviour
# is confirmed. Unknown values intentionally fall through to ``UNKNOWN``.
_STATUS_MAP: dict[str, PaymentStatus] = {
    # Creation / pending
    "created": PaymentStatus.CREATED,
    "new": PaymentStatus.CREATED,
    "pending": PaymentStatus.PENDING,
    "pending_validation": PaymentStatus.PENDING,
    "processing": PaymentStatus.PENDING,
    "in_progress": PaymentStatus.PENDING,
    # Authorized (funds held, not yet captured)
    "authorized": PaymentStatus.AUTHORIZED,
    "auth": PaymentStatus.AUTHORIZED,
    "pre_authorized": PaymentStatus.AUTHORIZED,
    # Captured / paid / success
    "captured": PaymentStatus.CAPTURED,
    "purchased": PaymentStatus.CAPTURED,
    "paid": PaymentStatus.CAPTURED,
    "success": PaymentStatus.CAPTURED,
    "successful": PaymentStatus.CAPTURED,
    "settled": PaymentStatus.CAPTURED,
    # Declined / failed
    "declined": PaymentStatus.DECLINED,
    "denied": PaymentStatus.DECLINED,
    "rejected": PaymentStatus.DECLINED,
    "failed": PaymentStatus.DECLINED,
    "failure": PaymentStatus.DECLINED,
    # Canceled / void
    "canceled": PaymentStatus.CANCELED,
    "cancelled": PaymentStatus.CANCELED,
    "voided": PaymentStatus.CANCELED,
    "void": PaymentStatus.CANCELED,
    # Refunds
    "refunded": PaymentStatus.REFUNDED,
    "partially_refunded": PaymentStatus.PARTIALLY_REFUNDED,
    "partial_refund": PaymentStatus.PARTIALLY_REFUNDED,
    # Expired
    "expired": PaymentStatus.EXPIRED,
    "timeout": PaymentStatus.EXPIRED,
    # Error
    "error": PaymentStatus.ERROR,
}

# SIBS Payment Gateway return codes (``returnStatus.statusCode``) seen in practice.
# ``"000"`` means success. These are mapped conservatively as well.
_STATUS_CODE_MAP: dict[str, PaymentStatus] = {
    "000": PaymentStatus.CAPTURED,
}


def normalize_payment_status(raw_status: str | None) -> PaymentStatus:
    """Map a raw SIBS status string onto a normalized :class:`PaymentStatus`.

    Never raises. Unrecognised or empty values map to :attr:`PaymentStatus.UNKNOWN`.
    """
    if raw_status is None:
        return PaymentStatus.UNKNOWN

    key = str(raw_status).strip().lower()
    if not key:
        return PaymentStatus.UNKNOWN

    if key in _STATUS_MAP:
        return _STATUS_MAP[key]

    # Some endpoints return numeric-ish status codes (e.g. "000").
    if key in _STATUS_CODE_MAP:
        return _STATUS_CODE_MAP[key]

    return PaymentStatus.UNKNOWN
