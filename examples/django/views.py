"""Minimal Django integration example (views).

This is illustrative; wire it up with ``urls.py`` and ``settings_example.py``.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pysibs import (
    SIBSClient,
    SIBSInvalidWebhookSignature,
    build_acknowledgement,
    decrypt_webhook,
    parse_webhook,
)

# A module-level client is fine; it is safe to share across requests.
client = SIBSClient.from_env()


@require_POST
def create_payment(request: HttpRequest) -> JsonResponse:
    body = json.loads(request.body or b"{}")
    payment = client.create_payment(
        amount=str(body["amount"]),
        currency=body.get("currency", "EUR"),
        merchant_transaction_id=body["order_id"],
        return_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    return JsonResponse(
        {"id": payment.id, "status": payment.status, "redirect_url": payment.redirect_url}
    )


def payment_status(request: HttpRequest, payment_id: str) -> JsonResponse:
    status = client.get_payment_status(payment_id)
    return JsonResponse({"payment_id": status.payment_id, "status": status.status})


@csrf_exempt
@require_POST
def sibs_webhook(request: HttpRequest) -> HttpResponse:
    secret = settings.SIBS_WEBHOOK_SECRET

    # SIBS encrypts the body with AES-GCM; decrypt it before trusting the payload.
    try:
        data = decrypt_webhook(
            body=request.body,
            iv=request.headers["X-Initialization-Vector"],
            auth_tag=request.headers["X-Authentication-Tag"],
            secret=secret,
        )
    except SIBSInvalidWebhookSignature:
        return HttpResponse("invalid payload", status=400)

    event = parse_webhook(data)
    # ... update your order using event.payment_id / event.status ...
    print("sibs webhook:", event.payment_id, event.status)

    # Acknowledge with HTTP 200 so SIBS does not retry unnecessarily.
    return JsonResponse(build_acknowledgement(event))
