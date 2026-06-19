# Card payments (server-to-server) & 3D-Secure

> ⚠️ **PCI DSS.** Transmitting raw card data (PAN/CVV) through your server brings your
> environment into **PCI DSS scope**. Validate your integration with SIBS and your PCI
> advisor before using server-to-server card payments. PySIBS never stores or logs card
> data and does not model PAN/CVV fields.

> ℹ️ **Contract.** The endpoints and field names below are confirmed against the official
> SIBS documentation (`docs.pay.sibs.com`). PySIBS still accepts an **opaque** card body —
> you build the exact JSON — so it never holds card fields in its typed surface and you
> stay in control of what crosses the wire. The confirmed shape is documented here so you
> can build it correctly. Some token/recurring details vary between SIBS API versions
> (v1/v2) — verify against your integration's swagger.

The confirmed card request body (you build this and pass it as `card=`):

```jsonc
{
  "cardInfo": {
    "PAN": "4111111111111111",
    "secureCode": "123",
    "validationDate": "2030-12-31T00:00:00.000Z",  // expiry, full ISO-8601 datetime
    "cardholderName": "Jane Doe",
    "createToken": false                            // true to tokenize this card
  },
  "info": { "deviceInfo": { /* 3DS browser data, see below */ } }
}
```

## Flow

1. Create a payment with the `CARD` method — you get a `transaction_signature`.
2. Submit the card payload with `pay_with_card` (authenticates with `Authorization: Digest`).
3. If the result requires 3D-Secure (`paymentStatus: "Partial"`), redirect the shopper
   using the returned `action`, then call `submit_3ds`.

```python
payment = client.create_payment(
    amount="25.50", merchant_transaction_id="ORD-1", payment_methods=["CARD"]
)

# You build the exact body (opaque to PySIBS) — see the confirmed shape above:
result = client.pay_with_card(
    payment_id=payment.id,
    transaction_signature=payment.signature,
    card={"cardInfo": {"PAN": "...", "secureCode": "...",
                       "validationDate": "2030-12-31T00:00:00.000Z",
                       "cardholderName": "..."}},
)

if result.requires_3ds:
    # Redirect the shopper's browser to the 3DS challenge (auto-submitting POST form):
    from pysibs import render_3ds_redirect_html
    html = render_3ds_redirect_html(result.action)
    # ... return `html` as your HTTP response body ...

    # After the challenge returns, submit the 3DS step and resubmit as needed:
    final = client.submit_3ds(
        payment_id=payment.id,
        transaction_signature=payment.signature,
        data={"...": "..."},   # opaque 3DS/browser payload
    )
else:
    print(result.status)  # CAPTURED / DECLINED / ...
```

## `CardPaymentResponse`

| Field | Description |
| --- | --- |
| `payment_id` | Transaction id. |
| `status` | Normalized status (`CAPTURED`, `DECLINED`, `ACTION_REQUIRED`, …). |
| `raw_status` | Original `paymentStatus`. |
| `action` | `ActionResponse` for 3DS (when `requires_3ds`). |
| `requires_3ds` | `True` when a 3DS step is needed. |
| `raw_response` | Full untouched SIBS response. |

## `ActionResponse` & redirect helpers

`ActionResponse` carries `url`, `params` and `method` (default `POST`).

- `build_3ds_redirect(action)` → `{"method", "url", "fields"}` to render yourself.
- `render_3ds_redirect_html(action)` → a self-contained auto-submitting HTML page
  (all values HTML-escaped); return it as your response body.

## Tokenization & recurring payments

Ask SIBS to store a reusable token when paying, then charge it later (e.g. recurring /
merchant-initiated) without handling the PAN again.

```python
# 1) Tokenize on a card payment:
payment = client.create_payment(
    amount="9.99", merchant_transaction_id="SUB-1",
    payment_methods=["CARD"], tokenize=True,
)
result = client.pay_with_card(
    payment_id=payment.id, transaction_signature=payment.signature, card={...}
)
if result.token:
    store(result.token.value, result.token.expiry, result.token.masked_pan)

# 2) Later, charge the stored token. pay_with_token defaults to the `token/purchase`
#    endpoint; you build the opaque body. The docs reference `tokenInfo` for the token
#    and `merchantInitiatedTransaction` for MIT charges:
later = client.create_payment(
    amount="9.99", merchant_transaction_id="SUB-1-m2", payment_methods=["CARD"]
)
client.pay_with_token(
    payment_id=later.id,
    transaction_signature=later.signature,
    payload={
        "tokenInfo": {"value": "tok_...", "tokenType": "CARD"},
        "merchantInitiatedTransaction": {"type": "UCOF", "amountQualifier": "ESTIMATED"},
    },
)
```

The initial recurring may still trigger 3DS (`result.requires_3ds`); subsequent
merchant-initiated charges typically do not. Follow-up recurring charges target a
`.../{original-transaction-id}/recurring` endpoint referencing the original transaction —
pass it via `path=`. The exact `merchantInitiatedTransaction` enums differ between SIBS
API versions (e.g. `UCOF` vs recurring), so verify against your integration's swagger.

## 3DS browser data

3DS is **not** a separate endpoint: the device/browser info is sent inside the
`card/purchase` request under `info.deviceInfo`. `build_browser_data(...)` assembles the
`browser*` fields SIBS expects:

```python
from pysibs import build_browser_data

browser = build_browser_data(
    accept_header=request.headers["Accept"],
    user_agent=request.headers["User-Agent"],
    screen_width=1920, screen_height=1080, timezone_offset=-60,
)
result = client.pay_with_card(
    payment_id=payment.id,
    transaction_signature=payment.signature,
    card={"cardInfo": {...}, "info": {"deviceInfo": browser}},
)
```

A `Partial` status returns `actionResponse{type: "THREEDS_CHALLENGE", data{url, params}}`
to redirect the shopper. After the challenge you resubmit via `submit_3ds`; the exact
resubmit body/endpoint is not fully public, so it takes an opaque payload and an
overridable `path`.

## Endpoint overrides

`pay_with_card` defaults to `card/purchase` and `pay_with_token` to `token/purchase`
(both confirmed). `submit_3ds` defaults to `card/purchase` but the 3DS resubmit contract
is not fully public — override `path` to match your integration if it differs.
