"""Minimal FastAPI integration example.

    pip install "pysibs[examples]"
    uvicorn examples.fastapi.main:app --reload
"""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, Header, Request, Response

from pysibs import (
    SIBSClient,
    SIBSInvalidWebhookSignature,
    build_acknowledgement,
    decrypt_webhook,
    parse_webhook,
)

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
    x_initialization_vector: str = Header(...),
    x_authentication_tag: str = Header(...),
) -> Response:
    raw_body = await request.body()
    secret = os.environ["SIBS_WEBHOOK_SECRET"]

    # SIBS encrypts the body with AES-GCM; decrypt it before trusting the payload.
    try:
        data = decrypt_webhook(
            body=raw_body,
            iv=x_initialization_vector,
            auth_tag=x_authentication_tag,
            secret=secret,
        )
    except SIBSInvalidWebhookSignature:
        return Response(status_code=400, content="invalid payload")

    event = parse_webhook(data)
    # ... update your order using event.payment_id / event.status ...
    print("webhook:", event.payment_id, event.status)

    # Acknowledge with HTTP 200 so SIBS does not retry unnecessarily.
    return Response(status_code=200, content=json.dumps(build_acknowledgement(event)),
                    media_type="application/json")
