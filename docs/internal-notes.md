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
| Card S2S | create checkout (CARD) → POST card data with `Authorization: Digest {transactionSignature}`; statuses `Success`/`Declined`/`Pending`/`Partial` | `pay_with_card` (opaque) ✅ |
| 3D-Secure | `paymentStatus: "Partial"` → POST 3DS auth; `actionResponse.data.url` + `data.params` to redirect the browser (POST), then resubmit | `submit_3ds`, `ActionResponse`, `threeds` ✅ |
| Tokenization | checkout carries `tokenisation.tokenisationRequest.tokeniseCard=true`; success returns token value + expiry + masked card | `create_payment(tokenize=True)`, `CardToken` ✅ |
| Recurring / MIT | initial recurring (cardholder present) vs following (merchant-initiated) via stored token | `pay_with_token` (opaque) ✅ |
| Webhooks | Body **AES-GCM encrypted** (not HMAC); headers `X-Initialization-Vector`, `X-Authentication-Tag`, base64 body; ack with HTTP 200 + `{statusCode,statusMsg,notificationID}` | `webhooks.py` ✅ |
| Webhook payload | `returnStatus{statusCode,statusMsg}`, `paymentStatus`, `paymentMethod`, `transactionID`, `amount{value,currency}`, `merchant{transactionId,terminalId,merchantName}`, `notificationID`, `paymentReference` | `parse_webhook` ✅ |
| Webhook secret | AES key = **base64-decode of the Backoffice secret** (official Python/Java/C#/PHP samples all `base64.b64decode` it); raw key 16/24/32 bytes | `_coerce_key` ✅ |
| `paymentReference` fields | `entity`, `reference`, `amount{value,currency}`; expiry is `expireDate` (sync API) or `expiryDate` (webhook); webhook also has `paymentEntity`/`status` | `_extract_payment_reference` (accepts both) ✅ |
| Idempotency | No idempotency header documented; none sent | `idempotency.py` ✅ |
| Card endpoint + fields | `POST payments/{id}/card/purchase`; body `cardInfo{PAN, secureCode, validationDate (ISO-8601), cardholderName, createToken}`; `Authorization: Digest` + `X-IBM-Client-Id` | path in `client.py` ✅; body opaque (caller builds) |
| Token charge | `POST payments/{id}/token/purchase`; body `tokenInfo{value, tokenType, secureCode}`; response token in `tokenList[]{value, expireDate, maskedPAN}` | path + `_extract_card_token` ✅; charge body opaque |
| 3DS | **No separate endpoint** — browser/device data goes under `info.deviceInfo` in the `card/purchase` request; `Partial` → `actionResponse{id, type:"THREEDS_CHALLENGE", data{url,params}}`; **resubmit** by calling `card/purchase` again with `actionProcessed{id, type, executed}` (CARD API confirms `actionProcessed.type` enum `THREEDS_METHOD`/`THREEDS_CHALLENGE`/`DCC`) | `build_browser_data`, `_extract_action_response`, `build_3ds_resubmit` ✅ |
| MIT / recurring | `merchantInitiatedTransaction{type, validityDate, amountQualifier, description, schedule, active}`; `type` enum **`UCOF`** / **`RCRR`**; `amountQualifier` `DEFAULT`/`ESTIMATED`/`ACTUAL`; `originalTransaction{id, datetime, recipientId}` | docs in `cards.md` ✅ (payload opaque) |
| `deviceInfo` fields | `browserAcceptHeader, browserJavaEnabled, browserLanguage, browserColorDepth, browserScreenHeight, browserScreenWidth, browserTZ, browserUserAgent` (+ optional system/device fields); **no** `browserJavascriptEnabled` | `build_browser_data` ✅ |
| `tokenList` item | `tokenName, tokenType, value, maskedPAN, expireDate` | `_extract_card_token` ✅ |
| Sandbox host | Free Developer Portal sandbox is `https://sandbox.sibspayments.com/sibs/spg/v2` (swagger-confirmed); contracted quality host is `api.qly.sibspayments.com` | `config.py` note ✅ |

> Source for the above: Checkout API 2.0.1 + CARD API swagger, SIBS API Market sandbox
> (`developer.sibsapimarket.com/sandbox`, product node 3515 / Checkout node 13723),
> reviewed 2026-06.

## Still to confirm

| Area | Current assumption | To verify |
| --- | --- | --- |
| AES key bit-length | Length inferred from decoded secret (16/24/32) — accepted as-is, not a blocker | Whether the Backoffice secret is documented as a fixed 128/256-bit key (cosmetic). |

## Design guardrails

- Wire format isolated in `_payloads.py`; base URLs in `config.py`.
- Every response model preserves `raw_response` / `raw_payload`.
- Unknown statuses map to `PaymentStatus.UNKNOWN`; parsing never raises on them.
- Never invent endpoints, fields or headers; when unsure, keep it flexible and add a `NOTE`.
