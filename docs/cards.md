# Card payments (server-to-server) & 3D-Secure

> ⚠️ **PCI DSS.** Transmitting raw card data (PAN/CVV) through your server brings your
> environment into **PCI DSS scope**. Validate your integration with SIBS and your PCI
> advisor before using server-to-server card payments. PySIBS never stores or logs card
> data and does not model PAN/CVV fields.

> ⚠️ **Unverified contract.** SIBS' public documentation does not fully specify the card
> request fields or the exact card/3DS endpoint paths. PySIBS therefore accepts an
> **opaque** card payload (you build the exact body) and uses sensible default paths you
> can override. Confirm both against the SIBS Dev Portal for your integration.

## Flow

1. Create a payment with the `CARD` method — you get a `transaction_signature`.
2. Submit the card payload with `pay_with_card` (authenticates with `Authorization: Digest`).
3. If the result requires 3D-Secure (`paymentStatus: "Partial"`), redirect the shopper
   using the returned `action`, then call `submit_3ds`.

```python
payment = client.create_payment(
    amount="25.50", merchant_transaction_id="ORD-1", payment_methods=["CARD"]
)

# You build the exact body your verified contract requires (opaque to PySIBS):
result = client.pay_with_card(
    payment_id=payment.id,
    transaction_signature=payment.signature,
    card={"card": {"number": "...", "expiry": "MM/YY", "cvv": "..."}},
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

# 2) Later, charge the stored token (opaque payload you build per your contract):
later = client.create_payment(
    amount="9.99", merchant_transaction_id="SUB-1-m2", payment_methods=["CARD"]
)
client.pay_with_token(
    payment_id=later.id,
    transaction_signature=later.signature,
    payload={"token": {"value": "tok_..."}, "recurring": {"type": "FOLLOWING"}},
)
```

The initial recurring may still trigger 3DS (`result.requires_3ds`); subsequent
merchant-initiated charges typically do not.

## 3DS browser data

3DS authentication needs device/browser info. `build_browser_data(...)` assembles the
EMVCo-standard fields to include in your `submit_3ds` payload:

```python
from pysibs import build_browser_data

browser = build_browser_data(
    accept_header=request.headers["Accept"],
    user_agent=request.headers["User-Agent"],
    screen_width=1920, screen_height=1080, timezone_offset=-60,
)
client.submit_3ds(payment_id=..., transaction_signature=..., data={"browser": browser})
```

## Endpoint overrides

`pay_with_card(..., path="card-id/purchase")` and `submit_3ds(..., path="card-id/3ds")`
default to paths analogous to the MB WAY flow. Override `path` if your verified contract
differs.
