# PySIBS Roadmap

This is the exhaustive plan for taking PySIBS from a useful early SDK to a
**complete, production-grade, "nothing left to improve" library** for SIBS Gateway.

It is organised as:

1. **Released** — what already ships.
2. **Versioned milestones** — the ordered path to `1.0.0` and beyond.
3. **Cross-cutting tracks** — quality bars that apply to every release.
4. **Definition of "complete"** — the checklist that defines done.

The single source of truth for SIBS-contract uncertainties is
[`docs/internal-notes.md`](docs/internal-notes.md); when an item there is confirmed,
tick the matching box here and remove the related caveat from the README/docs.

Status legend: ✅ done · 🚧 in progress · ⏳ planned

---

## Released

### 0.1.0 ✅
Core sync/async clients; `create_payment`, `get_payment_status`, `refund_payment`,
`capture_payment`, `cancel_payment`; typed models; `Decimal` money; exception
hierarchy; webhook parsing; docs; CI + PyPI Trusted Publishing.

### 0.2.0 ✅
AES-GCM webhook decryption + acknowledgement; MB WAY purchase; MULTIBANCO reference
parsing; `AUTH`/`PURS` transaction types.

### 0.3.0 ✅
Card server-to-server (opaque payload) + 3D-Secure redirect handling
(`ActionResponse`, `pysibs.threeds`).

### 0.4.0 ✅
Card tokenization, token / recurring (merchant-initiated) payments, EMVCo 3DS
browser-data helper.

---

## Path to 1.0.0

### 0.5.0 — Contract hardening 🚧
Turn every "opaque / unverified" area into verified, typed models. Driven by the open
items in [`docs/internal-notes.md`](docs/internal-notes.md).

- [ ] Confirm and pin the webhook secret-key encoding for AES-GCM.
- [ ] Verify card / 3DS endpoint paths; drop the "unverified" caveat (keep `path=`
      overrides as an escape hatch).
- [ ] Type the card request body (still allowing a raw/opaque override for PCI-scope
      users who tokenize client-side).
- [ ] Type the 3DS authentication request (browser-data nesting + challenge result).
- [ ] Type token / recurring requests (initial vs following / MIT indicators).
- [ ] Confirm `paymentReference` field names across products.
- [ ] Confirm whether a dedicated idempotency header exists; wire it up if so.
- [ ] Map SIBS `returnStatus.statusCode` values to typed, documented error subclasses.
- [ ] Expand and verify the `PaymentStatus` mapping table per product/endpoint.

### 0.6.0 — Reliability & resilience ⏳
- [ ] Configurable automatic retries with exponential backoff + jitter for transient
      failures (timeouts, connection errors, 5xx) on idempotent operations only.
- [ ] Honour `Retry-After`; first-class `429 Too Many Requests` handling
      (`SIBSRateLimitError`).
- [ ] Idempotency-key generation/propagation helpers (once the header is confirmed).
- [ ] Granular timeouts (connect / read / write / pool) and connection-pool tuning.
- [ ] Proxy and custom-CA / TLS configuration passthrough.
- [ ] Deterministic, well-documented retry/timeout semantics with tests.

### 0.7.0 — Observability & security ⏳
- [ ] Pluggable, credential-safe logging hooks (request/response, redaction by default).
- [ ] Automatic PAN/CVV/secret masking in any log or error output.
- [ ] Request/response middleware hooks (e.g. for correlation IDs, metrics).
- [ ] Optional OpenTelemetry tracing/metrics integration (extra: `pysibs[otel]`).
- [ ] Webhook replay protection helper (notification-id dedupe guidance + utility).
- [ ] Secret rotation guidance for webhook keys; constant-time comparisons everywhere.
- [ ] Threat-model note in `SECURITY.md`; dependency/SBOM scanning in CI.

### 0.8.0 — Payment-method & API completeness ⏳
Cover the rest of the SIBS Gateway surface so no common flow requires dropping to raw
HTTP. Each item is gated on doc/sandbox verification.

- [ ] Hosted checkout / payment-form flow (`formContext`) — generate and return the
      redirect/form context for browser-redirect integrations.
- [ ] Digital wallets: Apple Pay and Google Pay payment flows.
- [ ] QR Code Express payments.
- [ ] vTerminal / MOTO payments.
- [ ] Token management: list, fetch and delete stored tokens (backoffice token APIs).
- [ ] Transaction lookup / reporting: fetch full transaction details and list/search
      transactions with pagination.
- [ ] Reconciliation / settlement report retrieval (if exposed by the API).
- [ ] Any remaining alternative payment methods SIBS exposes (BNPL, direct debit, …).

### 0.9.0 — DX, docs & release-candidate polish ⏳
- [ ] Hosted documentation site (MkDocs Material or Sphinx) with autodoc API reference.
- [ ] Lazy pagination iterators for all list endpoints (sync + async).
- [ ] Richer typed models for every response (no bare dicts on documented happy paths);
      `raw_*` always retained.
- [ ] Expanded examples: Flask, Celery worker, plain CLI, plus end-to-end recipes
      (full 3DS flow, refund/partial-refund, reconciliation, idempotent retries).
- [ ] Cookbook / how-to guides per payment method.
- [ ] Coverage raised to ≥ 95%; add property-based tests (money/validators) and a
      gated sandbox integration suite in CI.
- [ ] API ergonomics review (naming, kwargs, defaults) before freeze.

### 1.0.0 — Stable API ⏳
- [ ] All actively-used endpoints verified against the official SIBS contract; no
      "unverified" caveats remain on documented happy paths.
- [ ] Public API reviewed and **frozen**; documented deprecation policy + warnings.
- [ ] `DeprecationWarning`s added for any 0.x names being renamed/removed.
- [ ] Migration guide covering all breaking changes since 0.1.0.
- [ ] ≥ 95% coverage maintained; full `mypy --strict`; zero lint debt.
- [ ] `Development Status :: 5 - Production/Stable` classifier; docs site live.

---

## Beyond 1.0.0

### 1.1+ — Breadth & ecosystem ⏳
- [ ] Multi-market support (PT and other SIBS markets) via configurable endpoints.
- [ ] Optional framework integrations (Django app / DRF, FastAPI router) as separate
      extras, kept thin.
- [ ] Webhook event dataclasses per event type with discriminated unions.
- [ ] CLI tool (`pysibs ...`) for quick sandbox testing and reconciliation.

### 2.0.0 — Only if forced ⏳
- [ ] Reserved for a breaking change driven by a major SIBS API version. Accompanied by
      a full migration guide and a deprecation window on the prior major.

---

## Cross-cutting tracks (every release)

**Quality gates** (must stay green on each PR):
`ruff` clean · `mypy --strict` clean · tests pass on Python 3.10–3.13 (add new versions
as released) · coverage above threshold · `python -m build` + `twine check` pass.

**Project health** (set up early, maintained throughout):
- [ ] Issue/PR templates, `CODE_OF_CONDUCT.md`, `CODEOWNERS`.
- [ ] `pre-commit` hooks (ruff, mypy, end-of-file/whitespace).
- [ ] Dependabot / Renovate for dependencies and Actions.
- [ ] Release automation: changelog assembly + version bump on tag.
- [ ] Status badges (CI, PyPI, coverage, license, Python versions).
- [ ] Lower-bound dependency tests (oldest supported httpx/pydantic).

**Security & compliance** (continuous):
- [ ] Never store/log PAN, CVV, secrets; redact everywhere.
- [ ] Keep the PCI-scope guidance accurate as card features evolve.
- [ ] Supply-chain: pinned CI actions, SBOM, vulnerability scanning.

---

## Definition of "complete"

PySIBS is considered complete when **all** of the following hold:

1. **API coverage** — every SIBS Gateway operation a merchant realistically needs is a
   typed, documented method (payments across all methods, captures, refunds,
   cancellations, recurring/MIT, tokens incl. management, status, reporting, webhooks).
2. **Verified contract** — no "unverified/opaque" caveats remain for documented happy
   paths; `raw_*` access is still always available as an escape hatch.
3. **Reliability** — configurable retries/backoff, rate-limit and timeout handling, with
   deterministic, tested semantics.
4. **Security** — no sensitive data is ever stored or logged; PCI guidance is accurate;
   supply chain is hardened.
5. **Observability** — credential-safe logging + optional tracing hooks.
6. **DX** — full typing, sync/async parity, pagination, helpful typed errors, great docs
   site, examples for the major frameworks, and a clear migration/deprecation policy.
7. **Quality** — ≥ 95% coverage, strict typing, green CI across all supported Python
   versions, and reproducible, automated releases.

## Versioning

PySIBS follows [SemVer](https://semver.org/). On `0.x`, minor versions may include
breaking changes (documented in [`CHANGELOG.md`](CHANGELOG.md)); from `1.0.0` onward,
breaking changes require a major version bump and a deprecation window.
