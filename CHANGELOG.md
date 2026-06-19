# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/) and the format is based on
[Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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

[Unreleased]: https://github.com/robertruben98/pysibs/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/robertruben98/pysibs/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/robertruben98/pysibs/releases/tag/v0.1.0
