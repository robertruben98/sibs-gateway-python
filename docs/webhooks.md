# Webhooks

SIBS notifies your configured endpoint when a transaction's status changes — important
for asynchronous methods like MB WAY and MULTIBANCO references. Respond `200` quickly
so SIBS does not retry unnecessarily.

## Parsing

```python
from pysibs import parse_webhook

event = parse_webhook(raw_body)  # bytes, str or dict
event.event_type
event.payment_id
event.merchant_transaction_id
event.status       # normalized PaymentStatus
event.raw_status
event.raw_payload  # the full, untouched payload
```

`parse_webhook` never raises on an unknown status — it maps to `PaymentStatus.UNKNOWN`.

## Signature verification

SIBS' webhook signing scheme is not uniformly documented and may differ per
product/environment, so verification is a **configurable strategy**.

Default (HMAC-SHA256 of the raw body):

```python
from pysibs import verify_webhook_signature

ok = verify_webhook_signature(
    payload=raw_body,
    signature=request.headers.get("X-SIBS-Signature"),
    secret="webhook_secret",
)
```

Custom scheme:

```python
def my_verifier(body: bytes, signature: str) -> bool:
    ...  # implement SIBS' documented scheme for your integration
    return True

ok = verify_webhook_signature(raw_body, signature, verifier=my_verifier)
```

Use `raise_on_failure=True` to raise `SIBSInvalidWebhookSignature` instead of returning
`False`.

> **Always confirm the exact signing scheme against the official SIBS documentation
> before relying on it in production.**
