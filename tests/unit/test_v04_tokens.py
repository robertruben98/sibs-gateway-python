"""Tests for v0.4.0: tokenization, token/recurring payments, 3DS browser data."""

from __future__ import annotations

import httpx
import pytest
import respx

from pysibs import (
    AsyncSIBSClient,
    PaymentStatus,
    SIBSValidationError,
    build_browser_data,
)
from pysibs.client import SIBSClient

BASE = "https://sibs.test/sibs/spg/v2"
CARD = {"card": {"number": "4111111111111111", "expiry": "12/30", "cvv": "123"}}


@respx.mock
def test_create_payment_tokenize_adds_tokenisation(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "x", "paymentStatus": "pending"})
    )
    client.create_payment(
        amount="10.00", merchant_transaction_id="ORD-T", payment_methods=["CARD"], tokenize=True
    )
    body = route.calls.last.request.read().decode()
    assert '"tokeniseCard":true' in body
    assert "tokenisation" in body


@respx.mock
def test_create_payment_no_tokenisation_by_default(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "pending"})
    )
    client.create_payment(amount="10.00", merchant_transaction_id="ORD-N")
    assert "tokenisation" not in route.calls.last.request.read().decode()


@respx.mock
def test_pay_with_card_parses_token(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(
            200,
            json={
                "transactionID": "tx_1",
                "paymentStatus": "Success",
                "token": {
                    "value": "tok_abc123",
                    "expireDate": "2030-12",
                    "maskedPan": "411111******1111",
                },
            },
        )
    )
    result = client.pay_with_card(payment_id="tx_1", transaction_signature="sig", card=CARD)
    assert result.token is not None
    assert result.token.value == "tok_abc123"
    assert result.token.expiry == "2030-12"
    assert result.token.masked_pan == "411111******1111"


@respx.mock
def test_pay_with_card_parses_token_list(client: SIBSClient) -> None:
    # Official response shape: token carried in tokenList[] with capital-PAN masking.
    respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(
            200,
            json={
                "transactionID": "tx_1",
                "paymentStatus": "Success",
                "tokenList": [
                    {
                        "value": "tok_list_1",
                        "expireDate": "2031-08",
                        "maskedPAN": "411111******4242",
                        "tokenType": "CARD",
                    }
                ],
            },
        )
    )
    result = client.pay_with_card(payment_id="tx_1", transaction_signature="sig", card=CARD)
    assert result.token is not None
    assert result.token.value == "tok_list_1"
    assert result.token.expiry == "2031-08"
    assert result.token.masked_pan == "411111******4242"


@respx.mock
def test_pay_with_card_token_as_string(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "Success", "token": "tok_plain"})
    )
    result = client.pay_with_card(payment_id="tx_1", transaction_signature="sig", card=CARD)
    assert result.token is not None
    assert result.token.value == "tok_plain"


@respx.mock
def test_pay_with_card_no_token(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "Success"})
    )
    result = client.pay_with_card(payment_id="tx_1", transaction_signature="sig", card=CARD)
    assert result.token is None


@respx.mock
def test_pay_with_token(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_2/token/purchase").mock(
        return_value=httpx.Response(200, json={"transactionID": "tx_2", "paymentStatus": "Success"})
    )
    result = client.pay_with_token(
        payment_id="tx_2",
        transaction_signature="sig",
        payload={"token": {"value": "tok_abc123"}, "recurring": {"type": "FOLLOWING"}},
    )
    assert result.status is PaymentStatus.CAPTURED
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Digest sig"
    assert "tok_abc123" in request.read().decode()


def test_pay_with_token_rejects_empty(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.pay_with_token(payment_id="tx_2", transaction_signature="sig", payload={})


@respx.mock
async def test_async_pay_with_token() -> None:
    respx.post(f"{BASE}/payments/tx_a/token/purchase").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "Success"})
    )
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE) as client:
        result = await client.pay_with_token(
            payment_id="tx_a", transaction_signature="sig", payload={"token": "tok_x"}
        )
        assert result.status is PaymentStatus.CAPTURED


def test_build_browser_data() -> None:
    data = build_browser_data(
        accept_header="text/html",
        user_agent="Mozilla/5.0",
        screen_height=1080,
        screen_width=1920,
        timezone_offset=-60,
        java_enabled=False,
    )
    assert data["browserAcceptHeader"] == "text/html"
    assert data["browserUserAgent"] == "Mozilla/5.0"
    assert data["browserScreenWidth"] == "1920"
    assert data["browserScreenHeight"] == "1080"
    assert data["browserTZ"] == "-60"
    assert data["browserJavaEnabled"] is False
    assert data["browserColorDepth"] == "24"
    assert data["browserLanguage"] == "en-US"
    # SIBS' deviceInfo schema has no browserJavascriptEnabled field.
    assert "browserJavascriptEnabled" not in data
