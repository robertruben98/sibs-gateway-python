# Internal notes — SIBS Gateway assumptions

This file tracks the assumptions PySIBS makes about the SIBS Gateway API and the points
that must be confirmed against the **current official documentation** before treating
any function as production-stable. No credentials or private data belong here.

## Status: to be verified

| Area | Current assumption (in code) | Must confirm |
| --- | --- | --- |
| Base URLs | `api.qly.sibspayments.com/sibs/spg/v2` (sandbox), `api.sibspayments.com/sibs/spg/v2` (production) — `pysibs/config.py` | Exact hosts/paths and API version segment. |
| Auth | `Authorization: Bearer <api_key>`, optional `X-IBM-Client-Id: <client_id>` — `pysibs/_http.py` | Whether the client-id header is required and its exact name. |
| Create payment | `POST /payments` with `merchant` + `transaction` objects — `pysibs/_payloads.py` | Exact required fields, `paymentType`, amount encoding, URLs object. |
| Status | `GET /payments/{id}/status` | Exact path and response shape. |
| Refund | `POST /payments/{id}/refund` | Path and body (amount object, merchant ref field name). |
| Capture | `POST /payments/{id}/capture` | Path and body. |
| Cancel/void | `POST /payments/{id}/cancellation` | Path and body. |
| Status vocabulary | mapping table in `pysibs/enums.py` | Real status tokens / return codes per endpoint. |
| Webhook fields | keys tried in `pysibs/webhooks.py` (`transactionID`, `paymentStatus`, ...) | Real notification payload shape. |
| Webhook signature | HMAC-SHA256 default, configurable verifier | Whether/which signature SIBS sends and the algorithm. |
| Idempotency | no header sent by default — `pysibs/idempotency.py` | Whether a dedicated idempotency header exists. |

## Design guardrails

- Wire format is isolated in `pysibs/_payloads.py`; base URLs in `pysibs/config.py`.
  Adjust there once the contract is confirmed — clients don't change.
- Every response model preserves `raw_response` / `raw_payload`, so callers can reach
  any field PySIBS hasn't normalized.
- Unknown statuses map to `PaymentStatus.UNKNOWN`; parsing never raises on them.
- Never invent endpoints, fields or headers. When unsure, keep the interface flexible,
  add a `NOTE`, and don't advertise the function as stable.
