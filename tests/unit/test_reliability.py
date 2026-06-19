"""Tests for retries, rate limiting and transport options (0.6.0)."""

from __future__ import annotations

import httpx
import pytest
import respx

from pysibs import (
    PaymentStatus,
    RetryConfig,
    SIBSAPIError,
    SIBSClient,
    SIBSConnectionError,
    SIBSRateLimitError,
)
from pysibs._retry import retry_after_seconds

BASE = "https://sibs.test/sibs/spg/v2"

# Fast retries: no real sleeping.
FAST = RetryConfig(max_retries=2, backoff_factor=0, jitter=False)


def _client(**kw: object) -> SIBSClient:
    return SIBSClient(api_key="k", terminal_id="t", base_url=BASE, **kw)  # type: ignore[arg-type]


@respx.mock
def test_get_retries_on_503_then_succeeds() -> None:
    route = respx.get(f"{BASE}/payments/p1/status").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"paymentStatus": "paid"}),
        ]
    )
    client = _client(retries=FAST)
    status = client.get_payment_status("p1")
    assert status.status is PaymentStatus.CAPTURED
    assert route.call_count == 2
    client.close()


@respx.mock
def test_get_retries_on_connection_error_then_succeeds() -> None:
    route = respx.get(f"{BASE}/payments/p1/status").mock(
        side_effect=[
            httpx.ConnectError("boom"),
            httpx.Response(200, json={"paymentStatus": "paid"}),
        ]
    )
    client = _client(retries=FAST)
    assert client.get_payment_status("p1").status is PaymentStatus.CAPTURED
    assert route.call_count == 2
    client.close()


@respx.mock
def test_get_exhausts_retries_and_raises() -> None:
    respx.get(f"{BASE}/payments/p1/status").mock(return_value=httpx.Response(503))
    client = _client(retries=FAST)
    with pytest.raises(SIBSAPIError) as exc:
        client.get_payment_status("p1")
    assert exc.value.status_code == 503
    client.close()


@respx.mock
def test_post_retried_on_429_then_succeeds() -> None:
    route = respx.post(f"{BASE}/payments").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"transactionID": "x", "paymentStatus": "paid"}),
        ]
    )
    client = _client(retries=FAST)
    payment = client.create_payment(amount="1.00", merchant_transaction_id="O1")
    assert payment.status is PaymentStatus.CAPTURED
    assert route.call_count == 2
    client.close()


@respx.mock
def test_post_not_retried_on_500() -> None:
    route = respx.post(f"{BASE}/payments").mock(return_value=httpx.Response(500))
    client = _client(retries=FAST)
    with pytest.raises(SIBSAPIError):
        client.create_payment(amount="1.00", merchant_transaction_id="O1")
    assert route.call_count == 1  # POST not retried on 500
    client.close()


@respx.mock
def test_post_not_retried_on_connection_error() -> None:
    route = respx.post(f"{BASE}/payments").mock(side_effect=httpx.ConnectError("boom"))
    client = _client(retries=FAST)
    with pytest.raises(SIBSConnectionError):
        client.create_payment(amount="1.00", merchant_transaction_id="O1")
    assert route.call_count == 1  # never retried for non-idempotent
    client.close()


@respx.mock
def test_rate_limit_error_carries_retry_after_when_not_retried() -> None:
    respx.post(f"{BASE}/payments").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "12"})
    )
    client = _client(retries=0)  # disable retries
    with pytest.raises(SIBSRateLimitError) as exc:
        client.create_payment(amount="1.00", merchant_transaction_id="O1")
    assert exc.value.retry_after == 12.0
    assert isinstance(exc.value, SIBSAPIError)
    client.close()


def test_retry_config_validation() -> None:
    with pytest.raises(ValueError):
        RetryConfig(max_retries=-1)
    with pytest.raises(ValueError):
        RetryConfig(backoff_factor=-1)


def test_retry_config_int_shorthand() -> None:
    client = _client(retries=5)
    assert client._http._retries.max_retries == 5  # type: ignore[attr-defined]
    client.close()


def test_backoff_respects_retry_after_and_cap() -> None:
    cfg = RetryConfig(backoff_factor=1, max_backoff=10, jitter=False)
    assert cfg.backoff(0, retry_after=3) == 3.0
    assert cfg.backoff(99, retry_after=999) == 10.0  # capped
    assert cfg.backoff(2) == 4.0  # 1 * 2**2


@pytest.mark.parametrize(
    ("value", "expected"),
    [("5", 5.0), ("0", 0.0), (None, None), ("", None), ("garbage", None)],
)
def test_retry_after_seconds(value: str | None, expected: float | None) -> None:
    assert retry_after_seconds(value) == expected


@respx.mock
async def test_async_get_retries_on_503() -> None:
    from pysibs import AsyncSIBSClient

    route = respx.get(f"{BASE}/payments/p1/status").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"paymentStatus": "paid"}),
        ]
    )
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE, retries=FAST) as client:
        status = await client.get_payment_status("p1")
    assert status.status is PaymentStatus.CAPTURED
    assert route.call_count == 2


@respx.mock
async def test_async_post_not_retried_on_connection_error() -> None:
    from pysibs import AsyncSIBSClient

    route = respx.post(f"{BASE}/payments").mock(side_effect=httpx.ConnectError("boom"))
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE, retries=FAST) as client:
        with pytest.raises(SIBSConnectionError):
            await client.create_payment(amount="1.00", merchant_transaction_id="O1")
    assert route.call_count == 1


def test_client_accepts_granular_timeout_and_tls_opts() -> None:
    timeout = httpx.Timeout(connect=2.0, read=10.0, write=5.0, pool=1.0)
    client = SIBSClient(
        api_key="k", terminal_id="t", base_url=BASE, timeout=timeout, verify=True, proxy=None
    )
    assert client.config.timeout is timeout
    client.close()
