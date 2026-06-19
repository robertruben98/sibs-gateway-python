"""Synchronous SIBS Gateway client -- the main entry point of PySIBS."""

from __future__ import annotations

import httpx

from . import _payloads as P
from ._http import HTTPClient
from .config import DEFAULT_TIMEOUT, ClientConfig, SIBSEnvironment
from .idempotency import build_idempotency_headers
from .models import (
    OperationResponse,
    PaymentResponse,
    PaymentStatusResponse,
    RefundResponse,
)
from .money import Amount
from .validators import validate_payment_id

__all__ = ["SIBSClient"]


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
        timeout: float = DEFAULT_TIMEOUT,
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
            transport=transport,
        )

    @classmethod
    def from_env(
        cls,
        *,
        timeout: float = DEFAULT_TIMEOUT,
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
        description: str | None = None,
        return_url: str | None = None,
        cancel_url: str | None = None,
        payment_methods: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentResponse:
        """Create a payment and return a typed :class:`PaymentResponse`."""
        request = P.prepare_payment_request(
            amount=amount,
            currency=currency,
            merchant_transaction_id=merchant_transaction_id,
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
