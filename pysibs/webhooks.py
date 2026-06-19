"""Webhook parsing and signature verification.

SIBS sends webhook/notification callbacks to a merchant-configured endpoint to report
transaction status changes (especially important for asynchronous methods such as
MB WAY and MULTIBANCO references).

**Signature verification.** SIBS' webhook signing scheme is not uniformly documented
and may differ per product/environment. To avoid baking in an unverified assumption,
verification is implemented as a *configurable strategy*:

* :func:`verify_webhook_signature` defaults to an HMAC-SHA256 comparison, which is the
  most common scheme, but you can supply your own ``verifier`` callable that matches
  whatever SIBS actually uses for your integration.
* Always confirm the exact scheme against the official documentation before relying on
  it in production.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any

from .enums import normalize_payment_status
from .exceptions import SIBSInvalidWebhookSignature, SIBSValidationError
from .models import WebhookEvent

__all__ = [
    "parse_webhook",
    "verify_webhook_signature",
    "hmac_sha256_verifier",
    "SignatureVerifier",
]

# A verifier takes the raw request body and the provided signature and returns True
# when the signature is valid.
SignatureVerifier = Callable[[bytes, str], bool]


def _coerce_payload(payload: bytes | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload).decode("utf-8")
    elif isinstance(payload, str):
        raw = payload
    else:
        raise SIBSValidationError(
            f"Webhook payload must be bytes, str or dict; got {type(payload).__name__}."
        )
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SIBSValidationError("Webhook payload is not valid JSON.") from exc
    if not isinstance(data, dict):
        raise SIBSValidationError("Webhook payload must be a JSON object.")
    return data


def _first(payload: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-None value among ``keys`` (top level)."""
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def parse_webhook(payload: bytes | str | dict[str, Any]) -> WebhookEvent:
    """Parse a webhook body into a :class:`WebhookEvent`.

    Accepts the raw bytes/str body or an already-decoded dict. The original payload is
    always preserved on ``event.raw_payload``; status is normalized but never raises on
    unknown values.
    """
    data = _coerce_payload(payload)

    raw_status = _first(data, "paymentStatus", "status", "transactionStatus", "state")
    raw_status_str = str(raw_status) if raw_status is not None else None

    return WebhookEvent(
        event_type=_first(data, "notificationType", "eventType", "type"),
        payment_id=_first(data, "transactionID", "transactionId", "paymentId", "id"),
        merchant_transaction_id=_first(
            data, "merchantTransactionId", "merchant_transaction_id"
        ),
        status=normalize_payment_status(raw_status_str),
        raw_status=raw_status_str,
        raw_payload=data,
    )


def hmac_sha256_verifier(secret: str) -> SignatureVerifier:
    """Build an HMAC-SHA256 verifier for a given shared secret.

    The provided signature is compared (using a constant-time comparison) against the
    hex digest of ``HMAC-SHA256(secret, body)``. A leading ``"sha256="`` prefix, if
    present, is stripped before comparison.
    """
    secret_bytes = secret.encode("utf-8")

    def _verify(body: bytes, signature: str) -> bool:
        if not signature:
            return False
        candidate = signature.strip()
        if candidate.lower().startswith("sha256="):
            candidate = candidate[len("sha256=") :]
        expected = hmac.new(secret_bytes, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, candidate.lower())

    return _verify


def verify_webhook_signature(
    payload: bytes | str,
    signature: str | None,
    secret: str | None = None,
    *,
    verifier: SignatureVerifier | None = None,
    raise_on_failure: bool = False,
) -> bool:
    """Verify a webhook signature.

    Provide either a ``secret`` (uses the default HMAC-SHA256 scheme) or a custom
    ``verifier`` callable matching SIBS' documented scheme for your integration.

    Returns ``True``/``False`` by default. When ``raise_on_failure`` is set, a failed
    verification raises :class:`SIBSInvalidWebhookSignature` instead of returning
    ``False`` (handy for use inside request handlers).
    """
    if verifier is None and secret is None:
        raise SIBSValidationError(
            "verify_webhook_signature requires either a 'secret' or a 'verifier'."
        )

    if isinstance(payload, str):
        body = payload.encode("utf-8")
    elif isinstance(payload, (bytes, bytearray)):
        body = bytes(payload)
    else:
        raise SIBSValidationError("payload must be bytes or str for signature verification.")

    active_verifier = verifier if verifier is not None else hmac_sha256_verifier(str(secret))
    is_valid = bool(signature) and active_verifier(body, signature or "")

    if not is_valid and raise_on_failure:
        raise SIBSInvalidWebhookSignature("Webhook signature verification failed.")
    return is_valid
