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
- Create payments (purchase or pre-authorization), check status, refund, capture, cancel
- MB WAY purchase flow, MULTIBANCO reference parsing, and card (server-to-server) + 3D-Secure
- AES-GCM webhook decryption + acknowledgement helper (the scheme SIBS actually uses)
- Configurable, payment-safe retries with backoff; rate-limit (`429`) and granular
  timeout handling
- Credential-safe logging + PAN redaction helpers
- Typed Pydantic models with normalized statuses (`PaymentStatus`)
- Safe money handling with `Decimal` (floats are rejected)
- A clear exception hierarchy — raw `httpx` errors never leak out
- Fully typed (`py.typed`), `ruff` + `mypy --strict` clean

## Installation

```bash
pip install pysibs

# For AES-GCM webhook decryption (pulls in `cryptography`):
pip install "pysibs[webhooks]"
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

Create a pre-authorization, then capture (or cancel) it later:

```python
auth = client.create_payment(
    amount="25.50", merchant_transaction_id="ORDER-1", transaction_type="AUTH"
)
client.capture_payment(payment_id=auth.id, amount="25.50")
# or release it:
client.cancel_payment(auth.id)
```

## MB WAY

After creating a payment with the `MBWAY` method, trigger the purchase with the
shopper's phone (the result arrives via webhook):

```python
payment = client.create_payment(
    amount="10.00", merchant_transaction_id="ORDER-2", payment_methods=["MBWAY"]
)
client.pay_with_mbway(
    payment_id=payment.id,
    transaction_signature=payment.signature,
    customer_phone="351#911234567",
)
```

## MULTIBANCO reference

```python
payment = client.create_payment(
    amount="25.50", merchant_transaction_id="ORDER-3", payment_methods=["REFERENCE"]
)
ref = payment.payment_reference
print(ref.entity, ref.reference, ref.expire_date)  # show these to the shopper
```

## Async usage

```python
from pysibs import AsyncSIBSClient

async with AsyncSIBSClient.from_env() as client:
    payment = await client.create_payment(amount="10.00", merchant_transaction_id="ORDER-1")
```

## Card payments & 3D-Secure

> ⚠️ Transmitting raw card data brings your environment into **PCI DSS scope**. PySIBS
> never stores/logs card data and takes an **opaque** card payload (you build the body),
> so it does not model PAN/CVV. See [docs/cards.md](docs/cards.md).

```python
payment = client.create_payment(
    amount="25.50", merchant_transaction_id="ORD-1", payment_methods=["CARD"]
)
result = client.pay_with_card(
    payment_id=payment.id,
    transaction_signature=payment.signature,
    # opaque body; confirmed shape is cardInfo{PAN, secureCode, validationDate, ...}
    card={"cardInfo": {"PAN": "...", "secureCode": "...",
                       "validationDate": "2030-12-31T00:00:00.000Z"}},
)
if result.requires_3ds:
    from pysibs import render_3ds_redirect_html
    html = render_3ds_redirect_html(result.action)   # return as the HTTP response body
    # ...then client.submit_3ds(...) to finish.
```

## Webhooks

SIBS **encrypts** webhook bodies with AES-GCM (it does not sign them). Decrypt, parse,
then acknowledge with HTTP 200 so SIBS stops retrying:

```python
from pysibs import decrypt_webhook, parse_webhook, build_acknowledgement

data = decrypt_webhook(
    body=raw_body,                                   # base64 ciphertext (request body)
    iv=request.headers["X-Initialization-Vector"],
    auth_tag=request.headers["X-Authentication-Tag"],
    secret=WEBHOOK_SECRET_KEY,                        # from the SIBS Backoffice
)
event = parse_webhook(data)
print(event.payment_id, event.status, event.payment_reference)

ack = build_acknowledgement(event)   # return this JSON with HTTP 200
```

Requires `pip install "pysibs[webhooks]"`. See [docs/webhooks.md](docs/webhooks.md) for
details. The legacy `verify_webhook_signature()` helper remains for custom schemes but
SIBS Gateway does not use HMAC.

## Error handling

All exceptions inherit from `SIBSError`:

| Exception | Raised when |
| --- | --- |
| `SIBSConfigurationError` | The client is misconfigured (missing credentials, bad environment). |
| `SIBSValidationError` | Input fails local validation (e.g. a float amount, empty id). |
| `SIBSAuthenticationError` | SIBS rejects credentials (HTTP 401/403). |
| `SIBSAPIError` | Other API errors (carries `status_code` and `response_body`). |
| `SIBSRateLimitError` | HTTP 429 (subclass of `SIBSAPIError`); carries `retry_after`. |
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

## Reliability & observability

```python
from pysibs import SIBSClient, RetryConfig
import httpx

client = SIBSClient(
    api_key="...", terminal_id="...",
    retries=RetryConfig(max_retries=3, backoff_factor=0.5),   # or retries=3, or 0 to disable
    timeout=httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0),
    verify=True,          # TLS verification / path to a custom CA bundle
    proxy="http://proxy.local:8080",
)
```

Retries are **payment-safe by default**: idempotent reads (`GET`) retry on connection
errors, timeouts and retryable statuses, while `POST`s retry **only** on `429`/`503`
(where the request was not processed). `Retry-After` is honoured; HTTP 429 raises
`SIBSRateLimitError` with `retry_after` when retries are exhausted/disabled.

Logging is credential-safe — configure the `pysibs` logger to see request metadata
(method, path, status, elapsed); bodies, headers and credentials are never logged. Use
`mask_pan()` / `redact()` if you log payloads yourself, and `NotificationDeduplicator`
to ignore replayed webhooks.

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

As of `0.8.0` the core contract (webhook key, card/token endpoints, `tokenList`, the
`cardInfo`/3DS shape) is verified against the official docs; the few details still open
(MIT enums, the 3DS resubmit body, the AES key bit-length) are tracked in
[docs/internal-notes.md](docs/internal-notes.md). Before going to production, verify the
endpoints, payloads and webhook scheme against the current official SIBS documentation.

## Python compatibility

Tested on CPython 3.10, 3.11, 3.12 and 3.13.

## Roadmap

- `0.1.0` — `SIBSClient`/`AsyncSIBSClient`, create/status/refund/capture/cancel,
  webhook parsing, typed models, docs.
- `0.2.0` — AES-GCM webhook decryption + acknowledgement, MB WAY purchase flow,
  MULTIBANCO reference parsing, `AUTH`/`PURS` transaction types. ✅
- `0.3.0` — card server-to-server (opaque payload) + 3D-Secure redirect handling. ✅
- `0.4.0` — card tokenization, token / recurring payments, 3DS browser-data helper. ✅
- `0.6.0` — payment-safe retries with backoff, rate-limit (`429`) + granular timeouts. ✅
- `0.7.0` — credential-safe logging, PAN redaction, webhook deduplication. ✅
- `0.8.0` — contract hardening vs official docs: base64 webhook key, correct
  card/token endpoint paths, `tokenList` parsing, confirmed 3DS/`cardInfo` shape. ✅
- `0.9.0` — swagger-verified MIT enums (`UCOF`/`RCRR`), `deviceInfo` field names
  (dropped non-schema `browserJavascriptEnabled`), sandbox host note. ✅
- `1.0.0` — **stable API.** 3DS resubmit modelled (`build_3ds_resubmit`,
  `ActionResponse.id`); SIBS contract confirmed end-to-end against the official swagger. ✅

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Robert Benitez
