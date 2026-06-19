from __future__ import annotations

import httpx
import pytest
import respx

from pysibs import (
    AsyncSIBSClient,
    PaymentStatus,
    SIBSAPIError,
    SIBSAuthenticationError,
    SIBSClient,
    SIBSTimeoutError,
    SIBSValidationError,
)

BASE = "https://sibs.test/sibs/spg/v2"


@respx.mock
def test_create_payment_success(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(
            200,
            json={
                "transactionID": "tx_123",
                "transactionSignature": "sig_abc",
                "paymentStatus": "Success",
                "redirectUrl": "https://pay.test/redirect",
            },
        )
    )
    payment = client.create_payment(
        amount="25.50",
        currency="EUR",
        merchant_transaction_id="ORD-1001",
        return_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        payment_methods=["CARD", "MBWAY"],
    )
    assert route.called
    assert payment.id == "tx_123"
    assert payment.status is PaymentStatus.CAPTURED
    assert payment.raw_status == "Success"
    assert payment.redirect_url == "https://pay.test/redirect"
    assert payment.signature == "sig_abc"
    assert payment.raw_response["transactionID"] == "tx_123"

    # The request carried the bearer token and client id, and the correct payload.
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test_api_key"
    assert request.headers["X-IBM-Client-Id"] == "test-client-id"


@respx.mock
def test_create_payment_unknown_status_does_not_break(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "x", "paymentStatus": "ZORP"})
    )
    payment = client.create_payment(amount="1.00", merchant_transaction_id="ORD-2")
    assert payment.status is PaymentStatus.UNKNOWN
    assert payment.raw_status == "ZORP"


@respx.mock
def test_create_payment_api_error(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(400, json={"returnStatus": {"statusMsg": "bad"}})
    )
    with pytest.raises(SIBSAPIError) as excinfo:
        client.create_payment(amount="1.00", merchant_transaction_id="ORD-3")
    assert excinfo.value.status_code == 400
    assert excinfo.value.response_body == {"returnStatus": {"statusMsg": "bad"}}


@respx.mock
def test_auth_error_raises_authentication_error(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(return_value=httpx.Response(401, json={"error": "nope"}))
    with pytest.raises(SIBSAuthenticationError) as excinfo:
        client.create_payment(amount="1.00", merchant_transaction_id="ORD-4")
    # The API key must never leak into the exception message.
    assert "test_api_key" not in str(excinfo.value)


@respx.mock
def test_forbidden_raises_authentication_error(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(return_value=httpx.Response(403))
    with pytest.raises(SIBSAuthenticationError):
        client.create_payment(amount="1.00", merchant_transaction_id="ORD-4b")


@respx.mock
def test_server_error_raises_api_error(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(return_value=httpx.Response(500, text="oops"))
    with pytest.raises(SIBSAPIError) as excinfo:
        client.create_payment(amount="1.00", merchant_transaction_id="ORD-5")
    assert excinfo.value.status_code == 500


@respx.mock
def test_timeout_raises_sibs_timeout(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(SIBSTimeoutError):
        client.create_payment(amount="1.00", merchant_transaction_id="ORD-6")


@respx.mock
def test_http_408_maps_to_timeout(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments").mock(return_value=httpx.Response(408))
    with pytest.raises(SIBSTimeoutError):
        client.create_payment(amount="1.00", merchant_transaction_id="ORD-6b")


def test_create_payment_rejects_float(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.create_payment(amount=25.50, merchant_transaction_id="ORD-7")  # type: ignore[arg-type]


def test_create_payment_rejects_empty_merchant_id(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.create_payment(amount="1.00", merchant_transaction_id="")


def test_create_payment_production_requires_https() -> None:
    prod = SIBSClient(api_key="k", terminal_id="t", environment="production")
    with pytest.raises(SIBSValidationError):
        prod.create_payment(
            amount="1.00",
            merchant_transaction_id="ORD-8",
            return_url="http://insecure.test/x",
        )
    prod.close()


@respx.mock
def test_get_payment_status_success(client: SIBSClient) -> None:
    respx.get(f"{BASE}/payments/tx_123/status").mock(
        return_value=httpx.Response(
            200, json={"transactionID": "tx_123", "paymentStatus": "pending"}
        )
    )
    status = client.get_payment_status("tx_123")
    assert status.payment_id == "tx_123"
    assert status.status is PaymentStatus.PENDING
    assert status.raw_status == "pending"


def test_get_payment_status_validates_id(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.get_payment_status("")


@respx.mock
def test_refund_payment_full(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_123/refund").mock(
        return_value=httpx.Response(
            200, json={"transactionID": "rf_1", "paymentStatus": "refunded"}
        )
    )
    refund = client.refund_payment(payment_id="tx_123")
    assert refund.id == "rf_1"
    assert refund.payment_id == "tx_123"
    assert refund.status is PaymentStatus.REFUNDED
    # Full refund: no amount in the body.
    assert route.calls.last.request.content in (b"", b"{}")


@respx.mock
def test_refund_payment_partial(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_123/refund").mock(
        return_value=httpx.Response(
            200, json={"transactionID": "rf_2", "paymentStatus": "partially_refunded"}
        )
    )
    refund = client.refund_payment(
        payment_id="tx_123", amount="10.00", merchant_refund_id="REF-1"
    )
    assert refund.status is PaymentStatus.PARTIALLY_REFUNDED
    body = route.calls.last.request.read().decode()
    assert "10.0" in body
    assert "REF-1" in body


def test_refund_rejects_float(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.refund_payment(payment_id="tx_123", amount=10.0)  # type: ignore[arg-type]


@respx.mock
def test_capture_payment(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_123/capture").mock(
        return_value=httpx.Response(
            200, json={"transactionID": "tx_123", "paymentStatus": "captured"}
        )
    )
    result = client.capture_payment(payment_id="tx_123", amount="25.50")
    assert result.status is PaymentStatus.CAPTURED


@respx.mock
def test_cancel_payment(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_123/cancellation").mock(
        return_value=httpx.Response(
            200, json={"transactionID": "tx_123", "paymentStatus": "voided"}
        )
    )
    result = client.cancel_payment("tx_123")
    assert result.status is PaymentStatus.CANCELED


@respx.mock
def test_client_context_manager() -> None:
    with SIBSClient(api_key="k", terminal_id="t", base_url=BASE) as c:
        respx.get(f"{BASE}/payments/p1/status").mock(
            return_value=httpx.Response(200, json={"paymentStatus": "paid"})
        )
        assert c.get_payment_status("p1").status is PaymentStatus.CAPTURED


@respx.mock
def test_idempotency_header_sent_when_configured() -> None:
    client = SIBSClient(
        api_key="k", terminal_id="t", base_url=BASE, idempotency_header="X-Idempotency-Key"
    )
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "x", "paymentStatus": "paid"})
    )
    client.create_payment(
        amount="1.00", merchant_transaction_id="ORD-9", idempotency_key="ORD-9-key"
    )
    assert route.calls.last.request.headers["X-Idempotency-Key"] == "ORD-9-key"
    client.close()


@respx.mock
def test_idempotency_header_not_sent_by_default(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "x", "paymentStatus": "paid"})
    )
    client.create_payment(
        amount="1.00", merchant_transaction_id="ORD-10", idempotency_key="some-key"
    )
    # No undocumented header is sent.
    assert "X-Idempotency-Key" not in route.calls.last.request.headers


@respx.mock
async def test_async_create_payment() -> None:
    respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(200, json={"transactionID": "tx_a", "paymentStatus": "paid"})
    )
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE) as client:
        payment = await client.create_payment(amount="5.00", merchant_transaction_id="ORD-A")
        assert payment.id == "tx_a"
        assert payment.status is PaymentStatus.CAPTURED


@respx.mock
async def test_async_get_status_and_refund() -> None:
    respx.get(f"{BASE}/payments/tx_a/status").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "pending"})
    )
    respx.post(f"{BASE}/payments/tx_a/refund").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "refunded"})
    )
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE) as client:
        status = await client.get_payment_status("tx_a")
        assert status.status is PaymentStatus.PENDING
        refund = await client.refund_payment(payment_id="tx_a", amount="1.00")
        assert refund.status is PaymentStatus.REFUNDED
