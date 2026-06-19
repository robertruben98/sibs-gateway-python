# PySIBS Roadmap

This roadmap tracks where PySIBS has been and what remains before a stable `1.0.0`.
It complements [`docs/internal-notes.md`](docs/internal-notes.md), which lists the
specific parts of the SIBS contract still to be confirmed.

Status legend: ✅ released · 🚧 in progress · ⏳ planned

## Released

### 0.1.0 ✅
`SIBSClient` / `AsyncSIBSClient`, `create_payment` / `get_payment_status` /
`refund_payment` / `capture_payment` / `cancel_payment`, typed models, money handling,
exception hierarchy, webhook parsing, docs, CI + PyPI publishing.

### 0.2.0 ✅
AES-GCM webhook decryption + acknowledgement, MB WAY purchase flow, MULTIBANCO
reference parsing, `AUTH`/`PURS` transaction types.

### 0.3.0 ✅
Card server-to-server payments (opaque payload) + 3D-Secure redirect handling
(`ActionResponse`, `pysibs.threeds`).

### 0.4.0 ✅
Card tokenization, token / recurring (merchant-initiated) payments, EMVCo 3DS
browser-data helper.

## Planned

### 0.5.0 — Contract hardening 🚧
Replace the "opaque payload / unverified" areas with verified, typed models. Driven by
the open items in [`docs/internal-notes.md`](docs/internal-notes.md):

- [ ] Confirm and pin the webhook secret-key encoding for AES-GCM decryption.
- [ ] Verify card / 3DS endpoint paths and remove the "unverified" caveat (keep
      `path=` overrides as an escape hatch).
- [ ] Type the 3DS authentication request body (browser-data nesting SIBS expects).
- [ ] Type token / recurring requests (initial vs following / MIT indicators).
- [ ] Confirm `paymentReference` field names across products.
- [ ] Confirm whether a dedicated idempotency header exists; wire it up if so.

### 0.6.0 — Robustness & DX ⏳
- [ ] Optional retries with backoff for idempotent calls and 5xx/timeout.
- [ ] Structured (credential-safe) logging hooks.
- [ ] Pagination/reporting endpoints if applicable.
- [ ] Sandbox integration test suite run on demand in CI (gated, real credentials).

### 1.0.0 — Stable API ⏳
- [ ] All actively-used endpoints verified against the official SIBS contract.
- [ ] No "unverified" caveats on the documented happy paths.
- [ ] Public API reviewed and frozen; deprecation policy documented.
- [ ] ≥ 90% test coverage (currently ~91%) maintained.
- [ ] Migration guide for any breaking changes since 0.x.
- [ ] `Development Status :: 5 - Production/Stable` classifier.

## How this maps to issues

Each unchecked box above is a candidate GitHub issue. The single source of truth for
SIBS-contract uncertainties is [`docs/internal-notes.md`](docs/internal-notes.md); when
an item there is confirmed, tick the matching box here and drop the related caveat from
the README/docs.

## Versioning

PySIBS follows [SemVer](https://semver.org/). While on `0.x`, minor versions may
include breaking changes (documented in [`CHANGELOG.md`](CHANGELOG.md)); from `1.0.0`
onward, breaking changes require a major version bump.
