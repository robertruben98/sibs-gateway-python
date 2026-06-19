"""Synchronous SIBS Gateway client -- the main entry point of PySIBS."""

from __future__ import annotations

import httpx

from . import _payloads as P
from ._http import HTTPClient
from ._retry import RetryConfig
from ._retry import coerce_retries as _coerce_retries
from .config import DEFAULT_TIMEOUT, ClientConfig, SIBSEnvironment
from .enums import TransactionType
from .exceptions import SIBSValidationError
from .idempotency import build_idempotency_headers
from .models import (
    CardPaymentResponse,
    MBWayResponse,
    OperationResponse,
    PaymentResponse,
    PaymentStatusResponse,
    RefundResponse,
)
from .money import Amount
from .validators import validate_mbway_phone, validate_payment_id

__all__ = ["SIBSClient"]

# Default card endpoints (analogous to the MB WAY path). NOTE: the exact card/3DS paths
# are not fully documented publicly -- override via the ``path`` argument if needed.
_CARD_PURCHASE_PATH = "card-id/purchase"
_CARD_3DS_PATH = "card-id/3ds"


class SIBSClient:
    """A synchronous client for the SIBS Gateway API.

    The client is framework-agnostic and safe to share across requests. It can be used
    as a context manager to ensure the underlying HTTP connection pool is closed::

        with SIBSClient(api_key=..., terminal_id=...) as client:
            client.create_payment(...)
    """

    def __init__(
        self,
        api_key: str,
        terminal_id: str,
        environment: str | SIBSEnvironment = SIBSEnvironment.SANDBOX,
        *,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        retries: RetryConfig | int | None = None,
        verify: bool | str = True,
        proxy: str | None = None,
        client_id: str | None = None,
        webhook_secret: str | None = None,
        idempotency_header: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = ClientConfig.create(
            api_key=api_key,
            terminal_id=terminal_id,
            environment=environment,
            base_url=base_url,
            timeout=timeout,
            client_id=client_id,
            webhook_secret=webhook_secret,
        )
        self._idempotency_header = idempotency_header
        self._http = HTTPClient(
            base_url=self._config.base_url,
            api_key=self._config.api_key,
            client_id=self._config.client_id,
            timeout=self._config.timeout,
            retries=_coerce_retries(retries),
            verify=verify,
            proxy=proxy,
            transport=transport,
        )

    @classmethod
    def from_env(
        cls,
        *,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        retries: RetryConfig | int | None = None,
        verify: bool | str = True,
        proxy: str | None = None,
        base_url: str | None = None,
        idempotency_header: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> SIBSClient:
        """Construct a client from ``SIBS_*`` environment variables."""
        config = ClientConfig.from_env(timeout=timeout, base_url=base_url)
        return cls(
            api_key=config.api_key,
            terminal_id=config.terminal_id,
            environment=config.environment,
            base_url=config.base_url,
            timeout=config.timeout,
            retries=retries,
            verify=verify,
            proxy=proxy,
            client_id=config.client_id,
            webhook_secret=config.webhook_secret,
            idempotency_header=idempotency_header,
            transport=transport,
        )

    @property
    def config(self) -> ClientConfig:
        return self._config

    @property
    def _require_https(self) -> bool:
        # Allow http(s) in sandbox to ease local testing; require https in production.
        return self._config.environment is SIBSEnvironment.PRODUCTION

    def _idempotency_headers(self, key: str | None) -> dict[str, str]:
        return build_idempotency_headers(key, self._idempotency_header)

    def create_payment(
        self,
        *,
        amount: Amount,
        currency: str = "EUR",
        merchant_transaction_id: str,
        transaction_type: str | TransactionType = TransactionType.PURCHASE,
        tokenize: bool = False,
        description: str | None = None,
        return_url: str | None = None,
        cancel_url: str | None = None,
        payment_methods: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentResponse:
        """Create a payment and return a typed :class:`PaymentResponse`.

        ``transaction_type`` is ``PURS`` (purchase, captured immediately) by default;
        pass ``AUTH`` to pre-authorize and capture later via :meth:`capture_payment`.
        Set ``tokenize=True`` to ask SIBS to store a reusable card token on success
        (read it from the card response's ``token``).
        """
        request = P.prepare_payment_request(
            amount=amount,
            currency=currency,
            merchant_transaction_id=merchant_transaction_id,
            transaction_type=transaction_type,
            tokenize=tokenize,
            description=description,
            return_url=return_url,
            cancel_url=cancel_url,
            payment_methods=payment_methods,
            require_https=self._require_https,
        )
        payload = P.build_create_payment_payload(request, self._config.terminal_id)
        data = self._http.request(
            "POST", "/payments", json=payload, headers=self._idempotency_headers(idempotency_key)
        )
        return P.parse_create_payment_response(data)

    def pay_with_mbway(
        self,
        *,
        payment_id: str,
        transaction_signature: str,
        customer_phone: str,
        idempotency_key: str | None = None,
    ) -> MBWayResponse:
        """Trigger an MB WAY purchase on a previously created payment.

        This is the second step of the MB WAY flow: after :meth:`create_payment` with
        the ``MBWAY`` method, call this with the ``transaction_signature`` from that
        response and the shopper's ``customer_phone`` (format ``"351#911234567"``). SIBS
        then pushes a payment request to the MB WAY app; the final outcome arrives via
        webhook. This call authenticates with ``Authorization: Digest`` rather than the
        client's bearer token.
        """
        pid = validate_payment_id(payment_id)
        if not transaction_signature or not str(transaction_signature).strip():
            raise SIBSValidationError("transaction_signature is required for MB WAY.")
        phone = validate_mbway_phone(customer_phone)
        headers = {"Authorization": f"Digest {transaction_signature.strip()}"}
        headers.update(self._idempotency_headers(idempotency_key))
        data = self._http.request(
            "POST",
            f"/payments/{pid}/mbway-id/purchase",
            json=P.build_mbway_payload(phone),
            headers=headers,
        )
        return P.parse_mbway_response(data, pid)

    def pay_with_card(
        self,
        *,
        payment_id: str,
        transaction_signature: str,
        card: dict[str, object],
        path: str = _CARD_PURCHASE_PATH,
        idempotency_key: str | None = None,
    ) -> CardPaymentResponse:
        """Submit a server-to-server card payment on a created payment.

        ``card`` is an **opaque** payload that you build to match your verified SIBS
        contract — PySIBS does not model raw PAN/CVV fields. The result may require a
        3D-Secure step: when ``response.requires_3ds`` is true, use ``response.action``
        with :mod:`pysibs.threeds` to redirect the shopper, then call
        :meth:`submit_3ds`.

        .. warning::
           Transmitting raw card data brings your environment into PCI DSS scope.
        """
        return self._digest_post(
            payment_id=payment_id,
            transaction_signature=transaction_signature,
            path=path,
            body=P.build_card_payload(card),
            idempotency_key=idempotency_key,
        )

    def submit_3ds(
        self,
        *,
        payment_id: str,
        transaction_signature: str,
        data: dict[str, object],
        path: str = _CARD_3DS_PATH,
        idempotency_key: str | None = None,
    ) -> CardPaymentResponse:
        """Submit the 3D-Secure authentication step for a card payment.

        ``data`` is an opaque payload (e.g. browser/challenge data) per your verified
        contract. Returns the updated :class:`CardPaymentResponse`.
        """
        return self._digest_post(
            payment_id=payment_id,
            transaction_signature=transaction_signature,
            path=path,
            body=P.build_card_payload(data),
            idempotency_key=idempotency_key,
        )

    def pay_with_token(
        self,
        *,
        payment_id: str,
        transaction_signature: str,
        payload: dict[str, object],
        path: str = _CARD_PURCHASE_PATH,
        idempotency_key: str | None = None,
    ) -> CardPaymentResponse:
        """Charge a previously stored card token (incl. recurring / merchant-initiated).

        Create a payment first (with the ``CARD`` method), then submit an **opaque**
        ``payload`` referencing the stored token — you build the exact body (token id,
        and any initial/following recurring or MIT indicators) to match your verified
        SIBS contract. Returns a :class:`CardPaymentResponse` (may still require 3DS for
        an initial recurring).
        """
        return self._digest_post(
            payment_id=payment_id,
            transaction_signature=transaction_signature,
            path=path,
            body=P.build_card_payload(payload),
            idempotency_key=idempotency_key,
        )

    def _digest_post(
        self,
        *,
        payment_id: str,
        transaction_signature: str,
        path: str,
        body: dict[str, object],
        idempotency_key: str | None,
    ) -> CardPaymentResponse:
        pid = validate_payment_id(payment_id)
        if not transaction_signature or not str(transaction_signature).strip():
            raise SIBSValidationError("transaction_signature is required.")
        headers = {"Authorization": f"Digest {transaction_signature.strip()}"}
        headers.update(self._idempotency_headers(idempotency_key))
        response = self._http.request(
            "POST", f"/payments/{pid}/{path.strip('/')}", json=body, headers=headers
        )
        return P.parse_card_response(response, pid)

    def get_payment_status(self, payment_id: str) -> PaymentStatusResponse:
        """Query the current status of a payment."""
        pid = validate_payment_id(payment_id)
        data = self._http.request("GET", f"/payments/{pid}/status")
        return P.parse_status_response(data, pid)

    def refund_payment(
        self,
        *,
        payment_id: str,
        amount: Amount | None = None,
        currency: str = "EUR",
        merchant_refund_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> RefundResponse:
        """Refund a payment, fully (``amount=None``) or partially."""
        request = P.prepare_refund_request(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            merchant_refund_id=merchant_refund_id,
        )
        payload = P.build_refund_payload(request)
        data = self._http.request(
            "POST",
            f"/payments/{request.payment_id}/refund",
            json=payload,
            headers=self._idempotency_headers(idempotency_key),
        )
        return P.parse_refund_response(data, request.payment_id)

    def capture_payment(
        self,
        *,
        payment_id: str,
        amount: Amount | None = None,
        currency: str = "EUR",
        idempotency_key: str | None = None,
    ) -> OperationResponse:
        """Capture a previously authorized payment, fully or partially."""
        request = P.prepare_refund_request(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            merchant_refund_id=None,
        )
        payload = P.build_refund_payload(request)
        data = self._http.request(
            "POST",
            f"/payments/{request.payment_id}/capture",
            json=payload,
            headers=self._idempotency_headers(idempotency_key),
        )
        return P.parse_operation_response(data, request.payment_id)

    def cancel_payment(
        self, payment_id: str, *, idempotency_key: str | None = None
    ) -> OperationResponse:
        """Cancel / void a payment."""
        pid = validate_payment_id(payment_id)
        data = self._http.request(
            "POST",
            f"/payments/{pid}/cancellation",
            json={},
            headers=self._idempotency_headers(idempotency_key),
        )
        return P.parse_operation_response(data, pid)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> SIBSClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
