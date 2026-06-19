"""Tests for AES-GCM webhook decryption and the v0.2.0 webhook surface."""

from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from pysibs import (
    SIBSConfigurationError,
    SIBSInvalidWebhookSignature,
    SIBSValidationError,
    build_acknowledgement,
    decrypt_webhook,
    parse_webhook,
)

# A 32-byte (256-bit) key, as configured in the SIBS Backoffice.
KEY = "0123456789abcdef0123456789abcdef"


def _encrypt(plaintext: bytes, key: str = KEY) -> tuple[str, str, str]:
    """Return (body_b64, iv_b64, tag_b64) the way SIBS sends them."""
    aesgcm = AESGCM(key.encode())
    nonce = b"123456789012"  # 12-byte nonce
    ct_and_tag = aesgcm.encrypt(nonce, plaintext, None)
    ciphertext, tag = ct_and_tag[:-16], ct_and_tag[-16:]
    return (
        base64.b64encode(ciphertext).decode(),
        base64.b64encode(nonce).decode(),
        base64.b64encode(tag).decode(),
    )


SAMPLE = {
    "returnStatus": {"statusMsg": "Success", "statusCode": "000"},
    "paymentStatus": "Success",
    "paymentMethod": "REFERENCE",
    "transactionID": "s24587y857mtjgnbt",
    "amount": {"currency": "EUR", "value": "20.0"},
    "merchant": {"transactionId": "ORD-55", "terminalId": "88845"},
    "notificationID": "20273954-0540-4bd3-8e01-234eds234cds",
    "paymentReference": {
        "entity": "12345",
        "reference": "999888777",
        "amount": {"value": "20.0", "currency": "EUR"},
        "expireDate": "2026-07-01T00:00:00Z",
    },
}


def test_decrypt_webhook_roundtrip() -> None:
    body, iv, tag = _encrypt(json.dumps(SAMPLE).encode())
    data = decrypt_webhook(body, iv, tag, KEY)
    assert data["transactionID"] == "s24587y857mtjgnbt"


def test_decrypt_then_parse() -> None:
    body, iv, tag = _encrypt(json.dumps(SAMPLE).encode())
    event = parse_webhook(decrypt_webhook(body, iv, tag, KEY))
    assert event.payment_id == "s24587y857mtjgnbt"
    assert event.merchant_transaction_id == "ORD-55"  # nested merchant.transactionId
    assert event.notification_id == "20273954-0540-4bd3-8e01-234eds234cds"
    assert event.payment_method == "REFERENCE"
    assert event.status.value == "captured"
    assert event.payment_reference is not None
    assert event.payment_reference.entity == "12345"
    assert event.payment_reference.reference == "999888777"


def test_decrypt_wrong_key_raises() -> None:
    body, iv, tag = _encrypt(json.dumps(SAMPLE).encode())
    with pytest.raises(SIBSInvalidWebhookSignature):
        decrypt_webhook(body, iv, tag, "f" * 32)


def test_decrypt_tampered_ciphertext_raises() -> None:
    body, iv, tag = _encrypt(json.dumps(SAMPLE).encode())
    tampered = base64.b64encode(b"\x00" + base64.b64decode(body)[1:]).decode()
    with pytest.raises(SIBSInvalidWebhookSignature):
        decrypt_webhook(tampered, iv, tag, KEY)


def test_decrypt_invalid_key_length() -> None:
    body, iv, tag = _encrypt(json.dumps(SAMPLE).encode())
    with pytest.raises(SIBSConfigurationError):
        decrypt_webhook(body, iv, tag, "tooshort")


def test_decrypt_invalid_base64() -> None:
    with pytest.raises(SIBSValidationError):
        decrypt_webhook("not base64!!", "also bad", "nope", KEY)


def test_decrypt_no_parse_returns_raw_text() -> None:
    body, iv, tag = _encrypt(b"plain text not json")
    data = decrypt_webhook(body, iv, tag, KEY, parse=False)
    assert data == {"raw": "plain text not json"}


def test_decrypt_non_json_with_parse_raises() -> None:
    body, iv, tag = _encrypt(b"plain text not json")
    with pytest.raises(SIBSValidationError):
        decrypt_webhook(body, iv, tag, KEY)


def test_build_acknowledgement_from_event() -> None:
    event = parse_webhook(SAMPLE)
    ack = build_acknowledgement(event)
    assert ack == {
        "statusCode": "200",
        "statusMsg": "Success",
        "notificationID": "20273954-0540-4bd3-8e01-234eds234cds",
    }


def test_build_acknowledgement_from_id() -> None:
    ack = build_acknowledgement("abc-123")
    assert ack["notificationID"] == "abc-123"


def test_build_acknowledgement_without_id() -> None:
    ack = build_acknowledgement(None)
    assert "notificationID" not in ack
    assert ack["statusCode"] == "200"
