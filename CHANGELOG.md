# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/) and the format is based on
[Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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

[Unreleased]: https://github.com/robertruben98/pysibs/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/robertruben98/pysibs/releases/tag/v0.1.0
