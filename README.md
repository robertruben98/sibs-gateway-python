# PySIBS

A modern, typed, developer-friendly Python SDK for [SIBS Gateway](https://www.sibsapimarket.com/) payment integrations.

PySIBS provides a clean API for payments, refunds, captures, cancellations, status
checks and webhook verification. It is framework-agnostic and works in Django,
FastAPI, Flask, Celery, CLI scripts — anywhere Python runs.

> **Project status: Alpha.** The public API surface is intentionally small and
> stable, but endpoint/field details are still being validated against SIBS' official
> documentation. Every response exposes a `raw_response` so you are never blocked by a
> field PySIBS has not yet normalized. See [Caveats](#caveats--unverified-details).

## Features

- Synchronous (`SIBSClient`) and asynchronous (`AsyncSIBSClient`) clients
- Create payments, check status, refund, capture and cancel
- Typed Pydantic models with normalized statuses (`PaymentStatus`)
- Safe money handling with `Decimal` (floats are rejected)
- Webhook parsing and configurable signature verification
- A clear exception hierarchy — raw `httpx` errors never leak out
- Fully typed (`py.typed`), `ruff` + `mypy --strict` clean

## Installation

```bash
pip install pysibs
```

Requires Python 3.10+.

## Configuration

Construct a client directly:

```python
from pysibs import SIBSClient

client = SIBSClient(
    api_key="your_api_key",
    terminal_id="your_terminal_id",
    environment="sandbox",  # or "production"
)
```

…or from environment variables (`SIBS_API_KEY`, `SIBS_TERMINAL_ID`,
`SIBS_ENVIRONMENT`, and optionally `SIBS_CLIENT_ID`, `SIBS_WEBHOOK_SECRET`):

```python
client = SIBSClient.from_env()
```

The **core library never reads `.env`** — only the bundled examples do, via
`python-dotenv`. See [`.env.example`](.env.example).

## Create a payment

```python
payment = client.create_payment(
    amount="10.00",                 # str, int or Decimal — never float
    currency="EUR",
    merchant_transaction_id="ORDER-123",
    return_url="https://example.com/payment/success",
    cancel_url="https://example.com/payment/cancel",
    payment_methods=["CARD", "MBWAY", "MULTIBANCO"],
)

print(payment.id)
print(payment.status)        # normalized PaymentStatus
print(payment.redirect_url)
print(payment.raw_response)  # untouched SIBS response
```

## Check payment status

```python
status = client.get_payment_status("payment_123")
print(status.status)      # normalized PaymentStatus
print(status.raw_status)  # original value from SIBS
```

## Refunds

```python
# Full refund
client.refund_payment(payment_id="payment_123")

# Partial refund
client.refund_payment(payment_id="payment_123", amount="10.00", merchant_refund_id="REF-1001")
```

## Capture & cancel

```python
client.capture_payment(payment_id="payment_123", amount="25.50")
client.cancel_payment("payment_123")
```

## Async usage

```python
from pysibs import AsyncSIBSClient

async with AsyncSIBSClient.from_env() as client:
    payment = await client.create_payment(amount="10.00", merchant_transaction_id="ORDER-1")
```

## Webhooks

```python
from pysibs import parse_webhook, verify_webhook_signature

event = parse_webhook(raw_body)         # bytes, str or dict
print(event.payment_id, event.status, event.raw_payload)

is_valid = verify_webhook_signature(
    payload=raw_body,
    signature=request.headers.get("X-SIBS-Signature"),
    secret="webhook_secret",
)
```

SIBS' webhook signing scheme is not uniformly documented and may differ per
product/environment. `verify_webhook_signature` defaults to HMAC-SHA256, but you can
pass a custom `verifier` callable that matches whatever SIBS actually uses for your
integration. **Always confirm the scheme against the official documentation.**

## Error handling

All exceptions inherit from `SIBSError`:

| Exception | Raised when |
| --- | --- |
| `SIBSConfigurationError` | The client is misconfigured (missing credentials, bad environment). |
| `SIBSValidationError` | Input fails local validation (e.g. a float amount, empty id). |
| `SIBSAuthenticationError` | SIBS rejects credentials (HTTP 401/403). |
| `SIBSAPIError` | Other API errors (carries `status_code` and `response_body`). |
| `SIBSTimeoutError` | The request times out (or HTTP 408). |
| `SIBSConnectionError` | SIBS cannot be reached (DNS/TCP/TLS). |
| `SIBSInvalidWebhookSignature` | A webhook signature fails verification. |

```python
from pysibs import SIBSError, SIBSAuthenticationError

try:
    client.create_payment(amount="10.00", merchant_transaction_id="ORDER-1")
except SIBSAuthenticationError:
    ...  # bad credentials
except SIBSError as exc:
    ...  # any other PySIBS failure
```

## PCI DSS note

This SDK does not store or process cardholder data by itself. However, some SIBS
server-to-server card payment flows may require the merchant environment to be PCI DSS
compliant. Always validate your integration scope with SIBS and your PCI advisor.

PySIBS deliberately:

- never stores PAN or CVV,
- never logs `Authorization` headers or credentials,
- ships no examples containing real card data.

## Caveats — unverified details

SIBS' public documentation does not pin down every endpoint, field name and signing
detail unambiguously, and they can vary by product/environment. Where there was
ambiguity, PySIBS:

1. keeps the wire format isolated in `pysibs/_payloads.py` and base URLs in
   `pysibs/config.py`, so they are trivial to adjust in one place;
2. preserves the full `raw_response` / `raw_payload` on every model;
3. never sends undocumented headers (e.g. idempotency — see `pysibs/idempotency.py`).

Before going to production, verify the endpoints, payloads and webhook signature
scheme against the current official SIBS documentation.

## Python compatibility

Tested on CPython 3.10, 3.11, 3.12 and 3.13.

## Roadmap

- `0.1.0` — `SIBSClient`/`AsyncSIBSClient`, create/status/refund/capture/cancel,
  webhook parsing + verification, typed models, docs.
- `0.2.0` — richer payment-method specific models (MB WAY, MULTIBANCO references).
- `1.0.0` — stable API once the SIBS contract is fully confirmed end-to-end.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Robert Benitez
