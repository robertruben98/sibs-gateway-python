"""Webhook decryption, parsing and acknowledgement.

SIBS sends webhook/notification callbacks to a merchant-configured endpoint to report
transaction status changes (especially important for asynchronous methods such as
MB WAY and MULTIBANCO references).

**Security model (verified against the official documentation).** SIBS does *not* sign
webhooks with HMAC — it **encrypts the whole body with AES-GCM**. The request carries:

* ``X-Initialization-Vector`` -- base64-encoded IV (nonce);
* ``X-Authentication-Tag`` -- base64-encoded GCM authentication tag;
* a base64-encoded ciphertext body, ``Content-Type: text/plain``.

Decrypt with :func:`decrypt_webhook` using the secret key configured in the SIBS
Backoffice, then :func:`parse_webhook` the resulting JSON. Finally, respond ``HTTP 200``
with the JSON from :func:`build_acknowledgement` so SIBS does not retry.

The legacy HMAC helpers (:func:`verify_webhook_signature`, :func:`hmac_sha256_verifier`)
are retained for backwards compatibility and custom schemes, but are **not** what SIBS
uses for the SIBS Gateway product.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any

from ._payloads import _extract_payment_reference
from .enums import normalize_payment_status
from .exceptions import (
    SIBSConfigurationError,
    SIBSInvalidWebhookSignature,
    SIBSValidationError,
)
from .models import WebhookEvent

__all__ = [
    "decrypt_webhook",
    "parse_webhook",
    "build_acknowledgement",
    "NotificationDeduplicator",
    "verify_webhook_signature",
    "hmac_sha256_verifier",
    "SignatureVerifier",
]

# A verifier takes the raw request body and the provided signature and returns True
# when the signature is valid.
SignatureVerifier = Callable[[bytes, str], bool]

_VALID_AES_KEY_LENGTHS = (16, 24, 32)


def _b64decode(value: str | bytes, field: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise SIBSValidationError(f"{field} is not valid base64.") from exc


def _coerce_key(secret: str | bytes) -> bytes:
    key = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
    if len(key) not in _VALID_AES_KEY_LENGTHS:
        raise SIBSConfigurationError(
            "Webhook secret key must be 16, 24 or 32 bytes for AES-GCM "
            f"(got {len(key)} bytes). Use the key configured in the SIBS Backoffice."
        )
    return key


def decrypt_webhook(
    body: str | bytes,
    iv: str,
    auth_tag: str,
    secret: str | bytes,
    *,
    parse: bool = True,
) -> dict[str, Any]:
    """Decrypt an AES-GCM encrypted SIBS webhook body.

    ``body`` is the base64-encoded ciphertext sent by SIBS, ``iv`` the value of the
    ``X-Initialization-Vector`` header and ``auth_tag`` the value of the
    ``X-Authentication-Tag`` header (both base64). ``secret`` is the key configured in
    the SIBS Backoffice.

    Returns the decrypted JSON object (when ``parse`` is true) or ``{"raw": <text>}``
    for a non-JSON plaintext. Raises :class:`SIBSInvalidWebhookSignature` if the
    ciphertext/tag fails authentication (tampered or wrong key), and
    :class:`SIBSConfigurationError` if the ``cryptography`` package is missing.
    """
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # pragma: no cover - exercised via env without extra
        raise SIBSConfigurationError(
            "Webhook decryption requires the 'cryptography' package. "
            "Install it with: pip install 'pysibs[webhooks]'."
        ) from exc

    key = _coerce_key(secret)
    ciphertext = _b64decode(body, "webhook body")
    nonce = _b64decode(iv, "X-Initialization-Vector")
    tag = _b64decode(auth_tag, "X-Authentication-Tag")

    aesgcm = AESGCM(key)
    try:
        # The cryptography API expects ciphertext with the tag appended.
        plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
    except InvalidTag as exc:
        raise SIBSInvalidWebhookSignature(
            "Webhook decryption failed: authentication tag mismatch (tampered payload "
            "or wrong secret key)."
        ) from exc

    text = plaintext.decode("utf-8")
    if not parse:
        return {"raw": text}
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SIBSValidationError("Decrypted webhook payload is not valid JSON.") from exc
    if not isinstance(data, dict):
        raise SIBSValidationError("Decrypted webhook payload must be a JSON object.")
    return data


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


def _merchant_transaction_id(data: dict[str, Any]) -> Any:
    # SIBS nests the merchant reference under merchant.transactionId, but older/other
    # shapes use a top-level key -- accept both.
    merchant = data.get("merchant")
    if isinstance(merchant, dict):
        nested = merchant.get("transactionId") or merchant.get("merchantTransactionId")
        if nested is not None:
            return nested
    return _first(data, "merchantTransactionId", "merchant_transaction_id")


def parse_webhook(payload: bytes | str | dict[str, Any]) -> WebhookEvent:
    """Parse a (decrypted) webhook body into a :class:`WebhookEvent`.

    Accepts the decrypted JSON as bytes/str or an already-decoded dict (e.g. the result
    of :func:`decrypt_webhook`). The original payload is always preserved on
    ``event.raw_payload``; status is normalized but never raises on unknown values.
    """
    data = _coerce_payload(payload)

    raw_status = _first(data, "paymentStatus", "status", "transactionStatus", "state")
    raw_status_str = str(raw_status) if raw_status is not None else None
    merchant_tx = _merchant_transaction_id(data)

    return WebhookEvent(
        event_type=_first(data, "notificationType", "eventType", "type"),
        notification_id=_first(data, "notificationID", "notificationId"),
        payment_id=_first(data, "transactionID", "transactionId", "paymentId", "id"),
        merchant_transaction_id=str(merchant_tx) if merchant_tx is not None else None,
        payment_method=_first(data, "paymentMethod", "payment_method"),
        status=normalize_payment_status(raw_status_str),
        raw_status=raw_status_str,
        payment_reference=_extract_payment_reference(data),
        raw_payload=data,
    )


def build_acknowledgement(
    notification: WebhookEvent | str | None,
    *,
    status_code: str = "200",
    status_msg: str = "Success",
) -> dict[str, str]:
    """Build the JSON body to return (with HTTP 200) so SIBS stops retrying.

    Accepts a :class:`WebhookEvent` or a raw notification id. Returns
    ``{"statusCode": ..., "statusMsg": ..., "notificationID": ...}``.
    """
    if isinstance(notification, WebhookEvent):
        notification_id = notification.notification_id
    else:
        notification_id = notification

    ack = {"statusCode": status_code, "statusMsg": status_msg}
    if notification_id is not None:
        ack["notificationID"] = str(notification_id)
    return ack


class NotificationDeduplicator:
    """In-memory guard against processing the same webhook notification twice.

    SIBS retries notifications until acknowledged, so the same ``notificationID`` can
    arrive more than once. Call :meth:`seen` (or :meth:`is_duplicate`) keyed on the
    notification id before acting on an event::

        dedup = NotificationDeduplicator()           # module/app-level singleton
        if dedup.seen(event.notification_id):
            return ack                               # already processed; just ack

    This is a process-local, bounded LRU set — fine for a single worker. For multiple
    workers/instances, back the dedupe with a shared store (Redis, DB) instead; this
    class documents the contract such a store should implement.
    """

    def __init__(self, maxlen: int = 10_000) -> None:
        if maxlen <= 0:
            raise SIBSValidationError("maxlen must be positive.")
        self._maxlen = maxlen
        # dict preserves insertion order -> cheap LRU eviction of the oldest entries.
        self._seen: dict[str, None] = {}

    def is_duplicate(self, notification_id: str | None) -> bool:
        """Return True if this id was already recorded (without recording it)."""
        return notification_id is not None and notification_id in self._seen

    def seen(self, notification_id: str | None) -> bool:
        """Record ``notification_id`` and return whether it had been seen before.

        A ``None`` id is treated as never-seen (cannot dedupe without an id).
        """
        if notification_id is None:
            return False
        if notification_id in self._seen:
            return True
        self._seen[notification_id] = None
        if len(self._seen) > self._maxlen:
            # Evict the oldest inserted id.
            oldest = next(iter(self._seen))
            del self._seen[oldest]
        return False


def hmac_sha256_verifier(secret: str) -> SignatureVerifier:
    """Build an HMAC-SHA256 verifier for a given shared secret.

    .. note::
       The SIBS Gateway does **not** sign webhooks with HMAC -- it encrypts them with
       AES-GCM (see :func:`decrypt_webhook`). This helper is kept for custom schemes
       and backwards compatibility only.
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
    """Verify a webhook signature using HMAC-SHA256 or a custom ``verifier``.

    .. note::
       Retained for backwards compatibility and custom integrations. The SIBS Gateway
       encrypts webhooks with AES-GCM rather than signing them; prefer
       :func:`decrypt_webhook` for SIBS Gateway notifications.
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
