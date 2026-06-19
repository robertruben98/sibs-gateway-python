# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/) and the format is based on
[Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.7.0] - 2026-06-19

Delivers the roadmap's reliability (0.6.0) and observability/security (0.7.0) scope.

### Added
- **Retries with backoff + jitter** (`RetryConfig`): transient failures are retried
  with conservative, payment-safe defaults — idempotent methods (`GET`) retry on
  connection errors, timeouts and retryable statuses; non-idempotent methods (`POST`)
  retry **only** on `429`/`503` (request not processed). Pass `retries=` (a
  `RetryConfig` or an `int`) to clients; `0` disables retries.
- **`SIBSRateLimitError`** (HTTP 429, subclass of `SIBSAPIError`) carrying `retry_after`;
  `Retry-After` headers are honoured for backoff.
- **Granular timeouts**: `timeout=` accepts an `httpx.Timeout` (connect/read/write/pool);
  plus `verify=` (TLS/custom CA) and `proxy=` passthrough.
- **Credential-safe logging**: the `pysibs` logger emits DEBUG records with
  method/path/status/elapsed/attempt only — never headers, bodies or credentials.
- **Redaction helpers** `mask_pan()` and `redact()` for safely logging payloads that may
  contain cardholder data.
- **`NotificationDeduplicator`** to guard against processing a retried webhook twice.

## [0.4.0] - 2026-06-19

Adds card tokenization, token / recurring payments and a 3DS browser-data helper,
grounded in the official SIBS documentation; see `docs/cards.md`.

### Added
- `create_payment(tokenize=True)` — asks SIBS to store a reusable card token on a
  successful card payment (sends `tokenisation.tokenisationRequest.tokeniseCard`).
- `CardToken` model (`value`, `expiry`, `masked_pan`); `CardPaymentResponse.token` is
  parsed from card responses.
- `pay_with_token()` (sync + async) — charge a stored token, including
  recurring / merchant-initiated payments, via an **opaque** payload (overridable path).
- `pysibs.threeds.build_browser_data()` — assembles EMVCo 3DS browser fields for the
  3DS authentication payload.

### Notes
- Token/recurring request fields and endpoints are not fully public; `pay_with_token`
  takes an opaque payload and `build_browser_data` uses EMVCo-standard names — verify
  per integration.

## [0.3.0] - 2026-06-19

Adds server-to-server card payments and 3D-Secure, grounded in the official SIBS
documentation; see `docs/cards.md` and `docs/internal-notes.md`.

### Added
- `pay_with_card()` (sync + async) — submits an **opaque** card payload (the caller
  builds the body; PySIBS does not model PAN/CVV) with `Authorization: Digest` auth.
- `submit_3ds()` (sync + async) — submits the 3D-Secure authentication step.
- `CardPaymentResponse` with a `requires_3ds` helper, and `ActionResponse` describing
  the 3DS redirect (`url`, `params`, `method`).
- `pysibs.threeds`: `build_3ds_redirect()` and `render_3ds_redirect_html()` (an
  auto-submitting, HTML-escaped redirect page).
- `PaymentStatus.ACTION_REQUIRED` (SIBS `"Partial"` → 3DS required).

### Notes
- Card/3DS endpoint paths default to `card-id/purchase` / `card-id/3ds` and are
  overridable via `path=`; the exact contract is not fully public — verify per
  integration. Transmitting card data brings your environment into PCI DSS scope.

## [0.2.0] - 2026-06-19

Grounded in a review of the official SIBS Gateway documentation
(`docs.pay.sibs.com`); see `docs/internal-notes.md`.

### Added
- `decrypt_webhook()` — AES-GCM decryption of SIBS webhook bodies using the
  `X-Initialization-Vector` and `X-Authentication-Tag` headers.
- `build_acknowledgement()` — builds the `{statusCode, statusMsg, notificationID}`
  body to return (HTTP 200) so SIBS stops retrying.
- `pay_with_mbway()` (sync + async) — MB WAY purchase step with `customer_phone` and
  `Authorization: Digest` auth.
- `transaction_type` argument on `create_payment` (`PURS` default, or `AUTH` to
  pre-authorize) and a `TransactionType` enum.
- `PaymentReference` model; `create_payment`/`get_payment_status` now parse the
  MULTIBANCO `paymentReference` (entity, reference, amount, expire date).
- Webhook parsing now extracts `notification_id`, `payment_method`, the nested
  `merchant.transactionId`, and `payment_reference`.
- Optional extra `pysibs[webhooks]` (depends on `cryptography`).

### Changed
- `PaymentMethod.MULTIBANCO` is now an alias of `PaymentMethod.REFERENCE` (the actual
  SIBS wire value is `"REFERENCE"`).

### Deprecated
- `verify_webhook_signature()` / `hmac_sha256_verifier()` — SIBS Gateway encrypts
  webhooks (AES-GCM) rather than signing them; kept for custom schemes only.

## [0.1.0] - 2026-06-19

### Added
- Initial `SIBSClient` (synchronous) and `AsyncSIBSClient` (asynchronous).
- `create_payment`, `get_payment_status`, `refund_payment`, `capture_payment` and
  `cancel_payment`.
- `from_env()` constructor reading `SIBS_*` environment variables.
- Typed Pydantic models with normalized `PaymentStatus` and preserved `raw_response`.
- `Decimal`-based money handling that rejects `float`.
- Webhook parsing (`parse_webhook`) and configurable signature verification
  (`verify_webhook_signature`, `hmac_sha256_verifier`).
- Full exception hierarchy under `SIBSError`; raw `httpx` errors never leak.
- Documentation, examples (Django/FastAPI), CI and PyPI publish workflows.

[Unreleased]: https://github.com/robertruben98/pysibs/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/robertruben98/pysibs/compare/v0.4.0...v0.7.0
[0.4.0]: https://github.com/robertruben98/pysibs/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/robertruben98/pysibs/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/robertruben98/pysibs/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/robertruben98/pysibs/releases/tag/v0.1.0
