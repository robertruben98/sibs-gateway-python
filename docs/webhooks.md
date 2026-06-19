# Webhooks

SIBS notifies your configured endpoint when a transaction's status changes — important
for asynchronous methods like MB WAY and MULTIBANCO references. Respond `200` quickly
with the acknowledgement body so SIBS does not retry.

## Security model: AES-GCM (not HMAC)

Per the official documentation, the SIBS Gateway **encrypts** the webhook body with
AES-GCM (it does not sign it). The request carries:

- `X-Initialization-Vector` — base64 IV (nonce)
- `X-Authentication-Tag` — base64 GCM authentication tag
- a base64-encoded ciphertext body, `Content-Type: text/plain`

Decryption requires the optional extra:

```bash
pip install "pysibs[webhooks]"
```

## Decrypt → parse → acknowledge

```python
from pysibs import decrypt_webhook, parse_webhook, build_acknowledgement

data = decrypt_webhook(
    body=raw_body,                                  # base64 ciphertext (request body)
    iv=request.headers["X-Initialization-Vector"],
    auth_tag=request.headers["X-Authentication-Tag"],
    secret=WEBHOOK_SECRET_KEY,                       # from the SIBS Backoffice (16/24/32 bytes)
)

event = parse_webhook(data)
print(event.payment_id, event.status, event.merchant_transaction_id)
print(event.payment_reference)   # for MULTIBANCO references

# Respond HTTP 200 with this JSON so SIBS stops retrying:
ack = build_acknowledgement(event)   # {"statusCode": "200", "statusMsg": "Success", "notificationID": ...}
```

- `decrypt_webhook` raises `SIBSInvalidWebhookSignature` if the tag doesn't match
  (tampered payload or wrong key), and `SIBSConfigurationError` if `cryptography` isn't
  installed or the key length is invalid.
- `parse_webhook` never raises on an unknown status — it maps to `PaymentStatus.UNKNOWN`
  and preserves `event.raw_payload`.

## `WebhookEvent` fields

| Field | Source |
| --- | --- |
| `event_type` | `notificationType` / `eventType` |
| `notification_id` | `notificationID` (echo it in the ACK) |
| `payment_id` | `transactionID` |
| `merchant_transaction_id` | `merchant.transactionId` (nested) |
| `payment_method` | `paymentMethod` (e.g. `REFERENCE`, `MBWAY`) |
| `status` / `raw_status` | normalized + original `paymentStatus` |
| `payment_reference` | `paymentReference` (entity, reference, amount, expire date) |
| `raw_payload` | full decrypted payload |

## Custom / legacy verification

`verify_webhook_signature()` and `hmac_sha256_verifier()` remain available for custom
schemes, but the SIBS Gateway does not use HMAC — prefer `decrypt_webhook` for SIBS
Gateway notifications.

> Always confirm the exact secret-key encoding and header names for your integration
> against the official SIBS documentation.
