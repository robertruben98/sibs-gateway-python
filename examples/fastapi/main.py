"""Minimal FastAPI integration example.

    pip install "pysibs[examples]"
    uvicorn examples.fastapi.main:app --reload
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, Request, Response

from pysibs import SIBSClient, parse_webhook, verify_webhook_signature

app = FastAPI(title="PySIBS FastAPI example")

# Create one client for the app's lifetime; it is safe to share across requests.
client = SIBSClient.from_env()


@app.post("/payments")
async def create_payment(order_id: str, amount: str) -> dict[str, object]:
    payment = client.create_payment(
        amount=amount,
        currency="EUR",
        merchant_transaction_id=order_id,
        return_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    return {"id": payment.id, "status": payment.status, "redirect_url": payment.redirect_url}


@app.get("/payments/{payment_id}")
async def payment_status(payment_id: str) -> dict[str, object]:
    status = client.get_payment_status(payment_id)
    return {"payment_id": status.payment_id, "status": status.status}


@app.post("/webhooks/sibs")
async def sibs_webhook(
    request: Request,
    x_sibs_signature: str | None = Header(default=None),
) -> Response:
    raw_body = await request.body()
    secret = os.environ.get("SIBS_WEBHOOK_SECRET", "")

    # Confirm SIBS' real signing scheme before relying on this in production.
    if secret and not verify_webhook_signature(raw_body, x_sibs_signature, secret=secret):
        return Response(status_code=400, content="invalid signature")

    event = parse_webhook(raw_body)
    # ... update your order using event.payment_id / event.status ...
    print("webhook:", event.payment_id, event.status)

    # Respond 200 quickly so SIBS does not retry unnecessarily.
    return Response(status_code=200)
