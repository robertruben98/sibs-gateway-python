"""Pure request-building and response-parsing helpers.

These functions contain no I/O. They translate between PySIBS' typed models and the
JSON shapes used by SIBS, and are shared by both the sync and async clients. Keeping
them pure makes the wire format easy to unit test and easy to adjust in one place once
the official SIBS contract is confirmed.

NOTE: the exact request/response field names below follow the SIBS Payment Gateway
(SPG) conventions but should be validated against the current official documentation.
Because every response model preserves the untouched ``raw_response``, callers are
never blocked by a field PySIBS has not mapped.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .enums import TransactionType, normalize_payment_status
from .exceptions import SIBSValidationError
from .models import (
    ActionResponse,
    CardPaymentResponse,
    CardToken,
    MBWayResponse,
    OperationResponse,
    PaymentReference,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    RefundRequest,
    RefundResponse,
)
from .money import Amount, normalize_amount
from .validators import (
    validate_currency,
    validate_merchant_transaction_id,
    validate_payment_id,
    validate_url,
)

JSONDict = dict[str, Any]


def prepare_payment_request(
    *,
    amount: Amount,
    currency: str,
    merchant_transaction_id: str,
    description: str | None,
    return_url: str | None,
    cancel_url: str | None,
    payment_methods: list[str] | None,
    transaction_type: str | TransactionType,
    tokenize: bool,
    require_https: bool,
) -> PaymentRequest:
    """Validate raw create_payment inputs and return a :class:`PaymentRequest`."""
    normalized_currency = validate_currency(currency)
    return PaymentRequest(
        amount=normalize_amount(amount, normalized_currency),
        currency=normalized_currency,
        merchant_transaction_id=validate_merchant_transaction_id(merchant_transaction_id),
        transaction_type=TransactionType.coerce(transaction_type).value,
        tokenize=tokenize,
        description=description,
        return_url=validate_url(return_url, require_https=require_https) if return_url else None,
        cancel_url=validate_url(cancel_url, require_https=require_https) if cancel_url else None,
        payment_methods=list(payment_methods) if payment_methods else None,
    )


def prepare_refund_request(
    *,
    payment_id: str,
    amount: Amount | None,
    currency: str,
    merchant_refund_id: str | None,
) -> RefundRequest:
    """Validate raw refund inputs and return a :class:`RefundRequest`."""
    normalized_currency = validate_currency(currency)
    return RefundRequest(
        payment_id=validate_payment_id(payment_id),
        amount=normalize_amount(amount, normalized_currency) if amount is not None else None,
        currency=normalized_currency,
        merchant_refund_id=merchant_refund_id,
    )


def _amount_obj(amount: Decimal, currency: str) -> JSONDict:
    # SIBS expects a numeric amount with a fixed number of decimals; we send it as a
    # JSON number derived from the already-quantized Decimal to avoid float artefacts.
    return {"value": float(amount), "currency": currency}


def _extract_status(data: JSONDict) -> tuple[str | None, str | None]:
    """Return ``(raw_status, status_code)`` pulled from common SIBS shapes."""
    raw_status: Any = None
    for key in ("paymentStatus", "status", "transactionStatus", "state"):
        if data.get(key) is not None:
            raw_status = data[key]
            break

    status_code: Any = None
    return_status = data.get("returnStatus")
    if isinstance(return_status, dict):
        status_code = return_status.get("statusCode")
        if raw_status is None:
            raw_status = return_status.get("statusMsg") or status_code

    raw = str(raw_status) if raw_status is not None else None
    code = str(status_code) if status_code is not None else None
    return raw, code


def _normalize(data: JSONDict) -> tuple[str | None, Any]:
    """Return ``(raw_status, normalized_status)`` for a response body."""
    raw_status, status_code = _extract_status(data)
    # Prefer the textual status; fall back to the numeric return code.
    normalized = normalize_payment_status(raw_status or status_code)
    return raw_status, normalized


def _extract_id(data: JSONDict) -> str | None:
    for key in ("transactionID", "transactionId", "id", "paymentId"):
        value = data.get(key)
        if value is not None:
            return str(value)
    return None


def _extract_redirect_url(data: JSONDict) -> str | None:
    for key in ("redirectUrl", "redirect_url", "url", "returnUrl"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    # Some flows nest a redirect under an action object.
    action = data.get("action")
    if isinstance(action, dict):
        for key in ("url", "redirectUrl"):
            value = action.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _extract_payment_reference(data: JSONDict) -> PaymentReference | None:
    """Parse a ``paymentReference`` object (MULTIBANCO), if present."""
    ref = data.get("paymentReference")
    if not isinstance(ref, dict) or not ref:
        return None

    amount = ref.get("amount")
    amount_value: Decimal | None = None
    currency: str | None = None
    if isinstance(amount, dict):
        raw_value = amount.get("value")
        if raw_value is not None:
            try:
                amount_value = Decimal(str(raw_value))
            except (ValueError, ArithmeticError):
                amount_value = None
        currency = amount.get("currency")

    return PaymentReference(
        entity=str(ref["entity"]) if ref.get("entity") is not None else None,
        reference=str(ref["reference"]) if ref.get("reference") is not None else None,
        amount=amount_value,
        currency=currency,
        expire_date=ref.get("expireDate") or ref.get("expirationDate") or ref.get("expiryDate"),
        raw=ref,
    )


def build_create_payment_payload(req: PaymentRequest, terminal_id: str) -> JSONDict:
    """Build the create-payment request body from a validated :class:`PaymentRequest`."""
    transaction: JSONDict = {
        "transactionTimestamp": datetime.now(timezone.utc).isoformat(),
        "description": req.description or req.merchant_transaction_id,
        "moto": False,
        "paymentType": req.transaction_type,
        "amount": _amount_obj(req.amount, req.currency),
    }
    if req.payment_methods:
        transaction["paymentMethod"] = list(req.payment_methods)

    if req.tokenize:
        # Ask SIBS to tokenize the card on a successful payment.
        transaction["tokenisation"] = {"tokenisationRequest": {"tokeniseCard": True}}

    payload: JSONDict = {
        "merchant": {
            "terminalId": terminal_id,
            "channel": "web",
            "merchantTransactionId": req.merchant_transaction_id,
        },
        "transaction": transaction,
    }
    if req.return_url:
        payload["urls"] = {"returnUrl": req.return_url}
        if req.cancel_url:
            payload["urls"]["cancelUrl"] = req.cancel_url
    elif req.cancel_url:
        payload["urls"] = {"cancelUrl": req.cancel_url}

    return payload


def parse_create_payment_response(data: JSONDict) -> PaymentResponse:
    raw_status, normalized = _normalize(data)
    return PaymentResponse(
        id=_extract_id(data),
        status=normalized,
        raw_status=raw_status,
        redirect_url=_extract_redirect_url(data),
        signature=data.get("transactionSignature") or data.get("signature"),
        payment_reference=_extract_payment_reference(data),
        raw_response=data,
    )


def parse_status_response(data: JSONDict, payment_id: str) -> PaymentStatusResponse:
    raw_status, normalized = _normalize(data)
    return PaymentStatusResponse(
        payment_id=_extract_id(data) or payment_id,
        status=normalized,
        raw_status=raw_status,
        payment_reference=_extract_payment_reference(data),
        raw_response=data,
    )


def build_refund_payload(req: RefundRequest) -> JSONDict:
    payload: JSONDict = {}
    if req.amount is not None:
        payload["amount"] = _amount_obj(req.amount, req.currency)
    if req.merchant_refund_id:
        payload["merchantTransactionId"] = req.merchant_refund_id
    return payload


def parse_refund_response(data: JSONDict, payment_id: str) -> RefundResponse:
    raw_status, normalized = _normalize(data)
    return RefundResponse(
        id=_extract_id(data),
        payment_id=payment_id,
        status=normalized,
        raw_status=raw_status,
        raw_response=data,
    )


def parse_operation_response(data: JSONDict, payment_id: str) -> OperationResponse:
    raw_status, normalized = _normalize(data)
    return OperationResponse(
        payment_id=_extract_id(data) or payment_id,
        status=normalized,
        raw_status=raw_status,
        raw_response=data,
    )


def _extract_action_response(data: JSONDict) -> ActionResponse | None:
    """Parse an ``actionResponse`` object (e.g. a 3D-Secure redirect), if present."""
    action = data.get("actionResponse") or data.get("action")
    if not isinstance(action, dict) or not action:
        return None

    inner = action.get("data")
    inner = inner if isinstance(inner, dict) else {}
    params = inner.get("params")
    if not isinstance(params, dict):
        params = {}

    return ActionResponse(
        type=action.get("type") or action.get("actionType"),
        method=str(inner.get("method") or action.get("method") or "POST").upper(),
        url=inner.get("url") or action.get("url"),
        params=params,
        raw=action,
    )


def _extract_card_token(data: JSONDict) -> CardToken | None:
    """Parse a stored-card token from a card response, if present.

    Per the official docs a successful tokenizing card payment returns the token under
    ``tokenList`` (an array of ``{value, expireDate, maskedPAN, tokenType}``); older /
    other shapes use a top-level ``token`` (string or object). All are accepted.
    """
    token: Any = data.get("token")
    if isinstance(token, str):
        return CardToken(value=token, raw={"token": token})
    if not isinstance(token, dict):
        # Preferred shape: tokenList[] (first entry).
        token_list = data.get("tokenList")
        if isinstance(token_list, list) and token_list and isinstance(token_list[0], dict):
            token = token_list[0]
        else:
            # Some responses nest it under a tokenisation/tokenInfo object.
            for key in ("tokenisation", "tokenInfo", "tokenisationResponse"):
                candidate = data.get(key)
                if isinstance(candidate, dict):
                    token = candidate
                    break
    if not isinstance(token, dict) or not token:
        return None

    return CardToken(
        value=(
            token.get("value") or token.get("token") or token.get("tokenValue") or token.get("id")
        ),
        expiry=token.get("expiry") or token.get("expireDate") or token.get("expirationDate"),
        masked_pan=token.get("maskedPan") or token.get("maskedPAN") or token.get("cardMasked"),
        raw=token,
    )


def build_card_payload(card: JSONDict) -> JSONDict:
    """Pass through an opaque card payload built by the caller.

    PySIBS deliberately does **not** model raw card fields (PAN/CVV) to avoid fixing an
    unverified contract and to keep cardholder data out of the library's typed surface.
    The caller supplies the exact JSON body their integration requires.
    """
    if not isinstance(card, dict) or not card:
        raise SIBSValidationError("card must be a non-empty dict (the SIBS card payload).")
    return card


def parse_card_response(data: JSONDict, payment_id: str) -> CardPaymentResponse:
    raw_status, normalized = _normalize(data)
    return CardPaymentResponse(
        payment_id=_extract_id(data) or payment_id,
        status=normalized,
        raw_status=raw_status,
        action=_extract_action_response(data),
        token=_extract_card_token(data),
        raw_response=data,
    )


def build_mbway_payload(customer_phone: str) -> JSONDict:
    """Build the MB WAY purchase request body.

    SIBS expects the phone as ``"<countryCode>#<number>"`` (e.g. ``"351#911234567"``).
    """
    return {"customerPhone": customer_phone}


def parse_mbway_response(data: JSONDict, payment_id: str) -> MBWayResponse:
    raw_status, normalized = _normalize(data)
    return MBWayResponse(
        payment_id=_extract_id(data) or payment_id,
        status=normalized,
        raw_status=raw_status,
        raw_response=data,
    )
