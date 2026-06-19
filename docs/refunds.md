# Refunds

## Full refund

```python
refund = client.refund_payment(payment_id="payment_123")
```

Omitting `amount` requests a full refund (no amount is sent in the request body).

## Partial refund

```python
refund = client.refund_payment(
    payment_id="payment_123",
    amount="10.00",
    currency="EUR",
    merchant_refund_id="REF-1001",
)
```

## `RefundResponse`

| Field | Description |
| --- | --- |
| `id` | Refund/transaction id from SIBS. |
| `payment_id` | The payment that was refunded. |
| `status` | Normalized `PaymentStatus` (e.g. `REFUNDED`, `PARTIALLY_REFUNDED`). |
| `raw_status` | Original status string. |
| `raw_response` | The full, untouched SIBS response. |

Amounts follow the same `Decimal`-only rules as payments (`float` is rejected).
