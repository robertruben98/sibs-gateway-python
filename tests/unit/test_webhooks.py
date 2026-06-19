from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from pysibs import (
    PaymentStatus,
    SIBSInvalidWebhookSignature,
    SIBSValidationError,
    hmac_sha256_verifier,
    parse_webhook,
    verify_webhook_signature,
)

SECRET = "webhook_secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_parse_valid_payload() -> None:
    payload = {
        "notificationType": "payment.status",
        "transactionID": "tx_55",
        "merchantTransactionId": "ORD-55",
        "paymentStatus": "Success",
    }
    raw = json.dumps(payload).encode()
    event = parse_webhook(raw)
    assert event.event_type == "payment.status"
    assert event.payment_id == "tx_55"
    assert event.merchant_transaction_id == "ORD-55"
    assert event.status is PaymentStatus.CAPTURED
    assert event.raw_status == "Success"
    assert event.raw_payload == payload


def test_webhook_parse_accepts_dict() -> None:
    event = parse_webhook({"transactionId": "x", "status": "pending"})
    assert event.payment_id == "x"
    assert event.status is PaymentStatus.PENDING


def test_webhook_parse_unknown_status() -> None:
    event = parse_webhook({"id": "x", "status": "weird"})
    assert event.status is PaymentStatus.UNKNOWN
    assert event.raw_status == "weird"


def test_webhook_parse_invalid_json() -> None:
    with pytest.raises(SIBSValidationError):
        parse_webhook(b"not-json")


def test_webhook_parse_non_object() -> None:
    with pytest.raises(SIBSValidationError):
        parse_webhook(b"[1, 2, 3]")


def test_webhook_valid_signature() -> None:
    body = b'{"transactionID": "tx_1"}'
    assert verify_webhook_signature(body, _sign(body), secret=SECRET) is True


def test_webhook_signature_with_prefix() -> None:
    body = b'{"a": 1}'
    sig = "sha256=" + _sign(body)
    assert verify_webhook_signature(body, sig, secret=SECRET) is True


def test_webhook_invalid_signature() -> None:
    body = b'{"transactionID": "tx_1"}'
    assert verify_webhook_signature(body, "deadbeef", secret=SECRET) is False


def test_webhook_invalid_signature_raises() -> None:
    body = b'{"transactionID": "tx_1"}'
    with pytest.raises(SIBSInvalidWebhookSignature):
        verify_webhook_signature(body, "bad", secret=SECRET, raise_on_failure=True)


def test_webhook_missing_signature() -> None:
    assert verify_webhook_signature(b"{}", None, secret=SECRET) is False


def test_webhook_requires_secret_or_verifier() -> None:
    with pytest.raises(SIBSValidationError):
        verify_webhook_signature(b"{}", "sig")


def test_webhook_custom_verifier() -> None:
    body = b"raw"
    called: dict[str, object] = {}

    def verifier(b: bytes, sig: str) -> bool:
        called["body"] = b
        called["sig"] = sig
        return sig == "ok"

    assert verify_webhook_signature(body, "ok", verifier=verifier) is True
    assert verify_webhook_signature(body, "no", verifier=verifier) is False
    assert called["body"] == body


def test_hmac_verifier_factory() -> None:
    verifier = hmac_sha256_verifier(SECRET)
    body = b'{"x": 1}'
    assert verifier(body, _sign(body)) is True
    assert verifier(body, "") is False


def test_webhook_string_payload_signature() -> None:
    body = '{"x": 1}'
    sig = _sign(body.encode())
    assert verify_webhook_signature(body, sig, secret=SECRET) is True
