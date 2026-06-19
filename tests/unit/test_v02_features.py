"""Tests for v0.2.0 client features: MB WAY, transaction type, MULTIBANCO reference."""

from __future__ import annotations

import httpx
import pytest
import respx

from pysibs import (
    PaymentMethod,
    PaymentStatus,
    SIBSValidationError,
    TransactionType,
)
from pysibs.client import SIBSClient as SyncClient

BASE = "https://sibs.test/sibs/spg/v2"


def test_payment_method_reference_alias() -> None:
    assert PaymentMethod.REFERENCE.value == "REFERENCE"
    assert PaymentMethod.MULTIBANCO.value == "REFERENCE"
    assert PaymentMethod.MULTIBANCO is PaymentMethod.REFERENCE


def test_transaction_type_coerce() -> None:
    assert TransactionType.coerce("auth") is TransactionType.AUTHORIZATION
    assert TransactionType.coerce("PURCHASE") is TransactionType.PURCHASE
    assert TransactionType.coerce(TransactionType.PURCHASE) is TransactionType.PURCHASE


def test_transaction_type_invalid() -> None:
    with pytest.raises(SIBSValidationError):
        TransactionType.coerce("nope")


@respx.mock
def test_create_payment_auth_sends_auth_payment_type(client: SyncClient) -> None:
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "x", "paymentStatus": "authorized"})
    )
    payment = client.create_payment(
        amount="10.00",
        merchant_transaction_id="ORD-AUTH",
        transaction_type="AUTH",
    )
    assert payment.status is PaymentStatus.AUTHORIZED
    body = route.calls.last.request.read().decode()
    assert '"paymentType":"AUTH"' in body


@respx.mock
def test_create_payment_default_is_purs(client: SyncClient) -> None:
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "x", "paymentStatus": "paid"})
    )
    client.create_payment(amount="10.00", merchant_transaction_id="ORD-PURS")
    assert '"paymentType":"PURS"' in route.calls.last.request.read().decode()


@respx.mock
def test_create_payment_parses_multibanco_reference(client: SyncClient) -> None:
    respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(
            200,
            json={
                "transactionID": "tx_ref",
                "paymentStatus": "pending",
                "paymentReference": {
                    "entity": "21800",
                    "reference": "123 456 789",
                    "amount": {"value": "25.50", "currency": "EUR"},
                    "expireDate": "2026-07-01T00:00:00Z",
                },
            },
        )
    )
    payment = client.create_payment(
        amount="25.50",
        merchant_transaction_id="ORD-REF",
        payment_methods=[PaymentMethod.REFERENCE],
    )
    assert payment.payment_reference is not None
    assert payment.payment_reference.entity == "21800"
    assert payment.payment_reference.reference == "123 456 789"
    assert str(payment.payment_reference.amount) == "25.50"
    assert payment.payment_reference.currency == "EUR"
    assert payment.payment_reference.expire_date == "2026-07-01T00:00:00Z"


@respx.mock
def test_pay_with_mbway(client: SyncClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_1/mbway-id/purchase").mock(
        return_value=httpx.Response(200, json={"transactionID": "tx_1", "paymentStatus": "pending"})
    )
    result = client.pay_with_mbway(
        payment_id="tx_1",
        transaction_signature="sig_xyz",
        customer_phone="351#911234567",
    )
    assert result.status is PaymentStatus.PENDING
    request = route.calls.last.request
    # MB WAY uses Digest auth (not the bearer token).
    assert request.headers["Authorization"] == "Digest sig_xyz"
    body = request.read().decode()
    assert "351#911234567" in body


def test_pay_with_mbway_requires_signature(client: SyncClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.pay_with_mbway(
            payment_id="tx_1", transaction_signature="", customer_phone="351#911234567"
        )


def test_pay_with_mbway_validates_phone(client: SyncClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.pay_with_mbway(
            payment_id="tx_1", transaction_signature="sig", customer_phone="911234567"
        )


@respx.mock
def test_create_payment_invalid_transaction_type(client: SyncClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.create_payment(
            amount="1.00", merchant_transaction_id="ORD", transaction_type="bogus"
        )


@respx.mock
async def test_async_pay_with_mbway() -> None:
    from pysibs import AsyncSIBSClient

    respx.post(f"{BASE}/payments/tx_a/mbway-id/purchase").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "pending"})
    )
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE) as client:
        result = await client.pay_with_mbway(
            payment_id="tx_a", transaction_signature="sig", customer_phone="351#911111111"
        )
        assert result.status is PaymentStatus.PENDING


def test_mbway_phone_validator_directly() -> None:
    from pysibs.validators import validate_mbway_phone

    assert validate_mbway_phone(" 351#911234567 ") == "351#911234567"
    with pytest.raises(SIBSValidationError):
        validate_mbway_phone("351-911234567")
