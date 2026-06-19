"""Tests for v0.3.0 card server-to-server + 3D-Secure support."""

from __future__ import annotations

import httpx
import pytest
import respx

from pysibs import (
    ActionResponse,
    AsyncSIBSClient,
    PaymentStatus,
    SIBSValidationError,
    build_3ds_redirect,
    render_3ds_redirect_html,
)
from pysibs.client import SIBSClient

BASE = "https://sibs.test/sibs/spg/v2"

# An opaque card payload -- the caller builds this; PySIBS does not model PAN/CVV.
CARD = {"card": {"number": "4111111111111111", "expiry": "12/30", "cvv": "123"}}

ACTION_RESPONSE = {
    "transactionID": "tx_1",
    "paymentStatus": "Partial",
    "actionResponse": {
        "type": "3DS",
        "data": {
            "url": "https://acs.test/challenge",
            "params": {"creq": "eyJ0aHJlZURT", "threeDSSessionData": "abc"},
        },
    },
}


@respx.mock
def test_pay_with_card_success(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(200, json={"transactionID": "tx_1", "paymentStatus": "Success"})
    )
    result = client.pay_with_card(
        payment_id="tx_1", transaction_signature="sig_xyz", card=CARD
    )
    assert result.status is PaymentStatus.CAPTURED
    assert result.requires_3ds is False
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Digest sig_xyz"
    assert "4111111111111111" in request.read().decode()


@respx.mock
def test_pay_with_card_requires_3ds(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(200, json=ACTION_RESPONSE)
    )
    result = client.pay_with_card(
        payment_id="tx_1", transaction_signature="sig", card=CARD
    )
    assert result.status is PaymentStatus.ACTION_REQUIRED
    assert result.requires_3ds is True
    assert result.action is not None
    assert result.action.url == "https://acs.test/challenge"
    assert result.action.params["creq"] == "eyJ0aHJlZURT"
    assert result.action.method == "POST"


@respx.mock
def test_pay_with_card_declined(client: SIBSClient) -> None:
    respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "Declined"})
    )
    result = client.pay_with_card(payment_id="tx_1", transaction_signature="s", card=CARD)
    assert result.status is PaymentStatus.DECLINED
    assert result.requires_3ds is False


def test_pay_with_card_rejects_empty_payload(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.pay_with_card(payment_id="tx_1", transaction_signature="s", card={})


def test_pay_with_card_requires_signature(client: SIBSClient) -> None:
    with pytest.raises(SIBSValidationError):
        client.pay_with_card(payment_id="tx_1", transaction_signature="", card=CARD)


@respx.mock
def test_submit_3ds(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_1/card/purchase").mock(
        return_value=httpx.Response(200, json={"transactionID": "tx_1", "paymentStatus": "Success"})
    )
    result = client.submit_3ds(
        payment_id="tx_1", transaction_signature="sig", data={"browser": {"userAgent": "x"}}
    )
    assert result.status is PaymentStatus.CAPTURED
    assert route.calls.last.request.headers["Authorization"] == "Digest sig"


@respx.mock
def test_pay_with_card_custom_path(client: SIBSClient) -> None:
    route = respx.post(f"{BASE}/payments/tx_1/custom/purchase").mock(
        return_value=httpx.Response(200, json={"paymentStatus": "Success"})
    )
    client.pay_with_card(
        payment_id="tx_1", transaction_signature="s", card=CARD, path="custom/purchase"
    )
    assert route.called


@respx.mock
async def test_async_pay_with_card() -> None:
    respx.post(f"{BASE}/payments/tx_a/card/purchase").mock(
        return_value=httpx.Response(200, json=ACTION_RESPONSE)
    )
    async with AsyncSIBSClient(api_key="k", terminal_id="t", base_url=BASE) as client:
        result = await client.pay_with_card(
            payment_id="tx_a", transaction_signature="sig", card=CARD
        )
        assert result.requires_3ds is True


def test_build_3ds_redirect() -> None:
    action = ActionResponse(
        url="https://acs.test/c", params={"creq": "abc"}, method="POST"
    )
    redirect = build_3ds_redirect(action)
    assert redirect == {
        "method": "POST",
        "url": "https://acs.test/c",
        "fields": {"creq": "abc"},
    }


def test_build_3ds_redirect_without_url_raises() -> None:
    with pytest.raises(SIBSValidationError):
        build_3ds_redirect(ActionResponse(params={"creq": "abc"}))


def test_render_3ds_redirect_html_escapes_and_autosubmits() -> None:
    action = ActionResponse(
        url="https://acs.test/c", params={"creq": "a<b>&c", "sess": "1"}
    )
    html = render_3ds_redirect_html(action)
    assert 'action="https://acs.test/c"' in html
    assert 'name="creq"' in html
    assert "a&lt;b&gt;&amp;c" in html  # HTML-escaped value
    assert "document.forms[0].submit()" in html


def test_render_3ds_redirect_html_no_autosubmit() -> None:
    action = ActionResponse(url="https://acs.test/c", params={})
    html = render_3ds_redirect_html(action, auto_submit=False)
    assert "document.forms[0].submit()" not in html
    assert "<button" in html
