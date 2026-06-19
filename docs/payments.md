# Payments

## Create a payment

```python
payment = client.create_payment(
    amount="25.50",                 # str, int or Decimal — never float
    currency="EUR",
    merchant_transaction_id="ORD-1001",
    description="Order 1001",       # optional
    return_url="https://example.com/success",
    cancel_url="https://example.com/cancel",
    payment_methods=["CARD", "MBWAY", "MULTIBANCO"],
    idempotency_key="ORD-1001-create",  # optional, see below
)
```

Returns a `PaymentResponse`:

| Field | Description |
| --- | --- |
| `id` | SIBS transaction id. |
| `status` | Normalized `PaymentStatus`. |
| `raw_status` | Original status string from SIBS. |
| `redirect_url` | URL to redirect the shopper to (if applicable). |
| `signature` | SIBS transaction signature (if returned). |
| `raw_response` | The full, untouched SIBS response. |

## Check status

```python
status = client.get_payment_status("payment_123")
status.status      # normalized PaymentStatus
status.raw_status  # original value
```

## Capture & cancel

```python
client.capture_payment(payment_id="payment_123", amount="25.50")
client.cancel_payment("payment_123")
```

## Money

Amounts are always handled as `Decimal`. Passing a `float` raises
`SIBSValidationError` (floats can't represent decimal money exactly). Use `str`, `int`
or `Decimal`. Amounts are quantized to the currency's minor units (2 for EUR) and must
be greater than zero.

## Idempotency

You may pass `idempotency_key` to `create_payment`/`refund_payment`/`capture_payment`.
Because SIBS does not clearly document a dedicated idempotency header, PySIBS does
**not** send any header by default — the key is validated but kept as metadata. If/when
SIBS confirms a header name, set it once via `idempotency_header=` on the client and
the key will be sent automatically. PySIBS never invents undocumented headers.
