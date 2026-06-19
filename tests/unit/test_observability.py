"""Tests for redaction and webhook replay protection (0.7.0)."""

from __future__ import annotations

import logging

import httpx
import pytest
import respx

from pysibs import (
    NotificationDeduplicator,
    SIBSClient,
    SIBSValidationError,
    mask_pan,
    redact,
)

BASE = "https://sibs.test/sibs/spg/v2"


def test_mask_pan_keeps_last_four() -> None:
    assert mask_pan("4111 1111 1111 1111") == "************1111"
    assert mask_pan("pan is 4111111111111111 ok") == "pan is ************1111 ok"


def test_mask_pan_leaves_short_numbers() -> None:
    assert mask_pan("order 12345") == "order 12345"


def test_redact_sensitive_keys_and_nested() -> None:
    payload = {
        "cardNumber": "4111111111111111",
        "cvv": "123",
        "merchantTransactionId": "ORD-1",
        "nested": {"securityCode": "999", "amount": {"value": 10}},
        "list": [{"token": "tok_x"}, "plain 4111111111111111"],
    }
    out = redact(payload)
    assert out["cardNumber"] == "***REDACTED***"
    assert out["cvv"] == "***REDACTED***"
    assert out["merchantTransactionId"] == "ORD-1"  # not sensitive
    assert out["nested"]["securityCode"] == "***REDACTED***"
    assert out["nested"]["amount"]["value"] == 10
    assert out["list"][0]["token"] == "***REDACTED***"
    assert out["list"][1] == "plain ************1111"
    # original is untouched
    assert payload["cardNumber"] == "4111111111111111"


def test_redact_authorization_key() -> None:
    assert redact({"Authorization": "Bearer secret"})["Authorization"] == "***REDACTED***"


def test_dedup_seen() -> None:
    dedup = NotificationDeduplicator()
    assert dedup.seen("n1") is False
    assert dedup.seen("n1") is True
    assert dedup.is_duplicate("n1") is True
    assert dedup.is_duplicate("n2") is False


def test_dedup_none_never_duplicate() -> None:
    dedup = NotificationDeduplicator()
    assert dedup.seen(None) is False
    assert dedup.seen(None) is False
    assert dedup.is_duplicate(None) is False


def test_dedup_eviction() -> None:
    dedup = NotificationDeduplicator(maxlen=2)
    dedup.seen("a")
    dedup.seen("b")
    dedup.seen("c")  # evicts "a"
    assert dedup.is_duplicate("a") is False
    assert dedup.is_duplicate("b") is True
    assert dedup.is_duplicate("c") is True


def test_dedup_invalid_maxlen() -> None:
    with pytest.raises(SIBSValidationError):
        NotificationDeduplicator(maxlen=0)


@respx.mock
def test_debug_logging_never_leaks_credentials(caplog: pytest.LogCaptureFixture) -> None:
    respx.get(f"{BASE}/payments/p1/status").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "paid"})
    )
    client = SIBSClient(api_key="super_secret_key", terminal_id="t", base_url=BASE)
    with caplog.at_level(logging.DEBUG, logger="pysibs"):
        client.get_payment_status("p1")
    blob = " ".join(r.getMessage() for r in caplog.records)
    assert "super_secret_key" not in blob
    assert "Bearer" not in blob
    assert "GET" in blob and "/payments/p1/status" in blob  # safe metadata is logged
    client.close()
