# Internal notes — SIBS Gateway assumptions

This file tracks what PySIBS assumes about the SIBS Gateway API and what has been
verified against the official documentation (`docs.pay.sibs.com`). No credentials or
private data belong here.

## Verified (docs.pay.sibs.com, reviewed 2026-06)

| Area | Confirmed behaviour | In code |
| --- | --- | --- |
| Base URLs | `api.qly.sibspayments.com` (quality/sandbox), `api.sibspayments.com` (production); path prefix `/sibs/spg/v2` | `config.py` ✅ |
| Auth | `Authorization: Bearer {token}` + `X-IBM-Client-Id: {clientId}` | `_http.py` ✅ |
| Create payment | `POST /payments` with `merchant{terminalId,channel,merchantTransactionId}` + `transaction{transactionTimestamp,description,moto,paymentType,amount{value,currency}}` + `paymentMethod[]` | `_payloads.py` ✅ |
| Payment type | `PURS` (purchase) / `AUTH` (pre-authorization) | `TransactionType` ✅ |
| Status / refund / capture / cancel | `GET /payments/{id}/status`, `POST /payments/{id}/refund`, `/capture`, `/cancellation` | clients ✅ |
| Payment method value | MULTIBANCO reference uses `"REFERENCE"` | `PaymentMethod` ✅ |
| MB WAY | 2-step: create checkout → `POST /payments/{id}/mbway-id/purchase` with `customerPhone:"351#9XXXXXXXX"` and `Authorization: Digest {transactionSignature}` | `pay_with_mbway` ✅ |
| Webhooks | Body **AES-GCM encrypted** (not HMAC); headers `X-Initialization-Vector`, `X-Authentication-Tag`, base64 body; ack with HTTP 200 + `{statusCode,statusMsg,notificationID}` | `webhooks.py` ✅ |
| Webhook payload | `returnStatus{statusCode,statusMsg}`, `paymentStatus`, `paymentMethod`, `transactionID`, `amount{value,currency}`, `merchant{transactionId,terminalId,merchantName}`, `notificationID`, `paymentReference` | `parse_webhook` ✅ |

## Still to confirm

| Area | Current assumption | To verify |
| --- | --- | --- |
| Webhook secret encoding | AES key = UTF-8 bytes of the Backoffice secret (16/24/32 bytes) | Exact key format/encoding SIBS expects. |
| `paymentReference` fields | `entity`, `reference`, `amount{value,currency}`, `expireDate` | Exact field names across products. |
| Idempotency | No header sent by default (`idempotency.py`) | Whether a dedicated idempotency header exists. |
| Card S2S flow | Not implemented | Full card form-context / 3DS flow (PCI scope). |

## Design guardrails

- Wire format isolated in `_payloads.py`; base URLs in `config.py`.
- Every response model preserves `raw_response` / `raw_payload`.
- Unknown statuses map to `PaymentStatus.UNKNOWN`; parsing never raises on them.
- Never invent endpoints, fields or headers; when unsure, keep it flexible and add a `NOTE`.
