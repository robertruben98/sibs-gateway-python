# Getting started

## Install

```bash
pip install pysibs
```

Requires Python 3.10+.

## Your first payment

```python
from pysibs import SIBSClient

client = SIBSClient(
    api_key="your_api_key",
    terminal_id="your_terminal_id",
    environment="sandbox",
)

payment = client.create_payment(
    amount="10.00",
    currency="EUR",
    merchant_transaction_id="ORDER-123",
)

print(payment.status)        # normalized PaymentStatus
print(payment.redirect_url)  # where to send the shopper, if applicable
print(payment.raw_response)  # untouched SIBS response
```

Close the client (or use it as a context manager) when you are done:

```python
with SIBSClient.from_env() as client:
    ...
```

## Async

```python
from pysibs import AsyncSIBSClient

async with AsyncSIBSClient.from_env() as client:
    payment = await client.create_payment(amount="10.00", merchant_transaction_id="ORDER-1")
```
