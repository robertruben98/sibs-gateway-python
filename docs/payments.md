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

## Transaction type (purchase vs authorization)

`create_payment` accepts `transaction_type` (`"PURS"` by default). Pass `"AUTH"` to
pre-authorize, then capture later:

```python
auth = client.create_payment(
    amount="25.50", merchant_transaction_id="ORD-1", transaction_type="AUTH"
)
client.capture_payment(payment_id=auth.id, amount="25.50")
```

## Capture & cancel

```python
client.capture_payment(payment_id="payment_123", amount="25.50")
client.cancel_payment("payment_123")
```

## MB WAY

After creating a payment with the `MBWAY` method, trigger the purchase. The shopper
approves it in the MB WAY app and the outcome arrives via webhook.

```python
payment = client.create_payment(
    amount="10.00", merchant_transaction_id="ORD-2", payment_methods=["MBWAY"]
)
client.pay_with_mbway(
    payment_id=payment.id,
    transaction_signature=payment.signature,
    customer_phone="351#911234567",   # "<countryCode>#<number>"
)
```

## MULTIBANCO reference

When the `REFERENCE` method is used, the response exposes a typed `payment_reference`:

```python
payment = client.create_payment(
    amount="25.50", merchant_transaction_id="ORD-3", payment_methods=["REFERENCE"]
)
ref = payment.payment_reference
print(ref.entity, ref.reference, ref.amount, ref.expire_date)
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
