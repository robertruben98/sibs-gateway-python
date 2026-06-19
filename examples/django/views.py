"""Minimal Django integration example (views).

This is illustrative; wire it up with ``urls.py`` and ``settings_example.py``.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from pysibs import SIBSClient, parse_webhook, verify_webhook_signature

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
    raw_body = request.body
    signature = request.headers.get("X-SIBS-Signature")
    secret = getattr(settings, "SIBS_WEBHOOK_SECRET", "")

    # Confirm SIBS' real signing scheme before relying on this in production.
    if secret and not verify_webhook_signature(raw_body, signature, secret=secret):
        return HttpResponse("invalid signature", status=400)

    event = parse_webhook(raw_body)
    # ... update your order using event.payment_id / event.status ...
    print("sibs webhook:", event.payment_id, event.status)

    # Respond 200 quickly so SIBS does not retry unnecessarily.
    return HttpResponse(status=200)
