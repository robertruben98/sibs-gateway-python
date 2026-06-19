# FastAPI integration

PySIBS has no FastAPI dependency; you just use the client inside your routes. Both the
sync `SIBSClient` and the `AsyncSIBSClient` work — use the async client to avoid
blocking the event loop on the HTTP call.

See the runnable example at [`examples/fastapi/main.py`](../examples/fastapi/main.py).

```bash
pip install "pysibs[examples]"
uvicorn examples.fastapi.main:app --reload
```

## Notes

- Construct the client once for the app's lifetime and reuse it.
- For the webhook endpoint, read the **raw** request body (`await request.body()`)
  before verifying the signature — re-serializing JSON would change the bytes.
- Respond `200` quickly so SIBS does not retry unnecessarily.

```python
from pysibs import AsyncSIBSClient

client = AsyncSIBSClient.from_env()

@app.post("/payments")
async def create(order_id: str, amount: str):
    return await client.create_payment(amount=amount, merchant_transaction_id=order_id)
```
