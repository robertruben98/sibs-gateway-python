"""Asynchronous SIBS Gateway client.

Mirrors :class:`~pysibs.client.SIBSClient` but uses ``async``/``await`` and an
``httpx.AsyncClient`` under the hood. All request building, validation and response
parsing is shared with the sync client via :mod:`pysibs._payloads`.
"""

from __future__ import annotations

import httpx

from . import _payloads as P
from ._http import AsyncHTTPClient
from .config import DEFAULT_TIMEOUT, ClientConfig, SIBSEnvironment
from .enums import TransactionType
from .exceptions import SIBSValidationError
from .idempotency import build_idempotency_headers
from .models import (
    MBWayResponse,
    OperationResponse,
    PaymentResponse,
    PaymentStatusResponse,
    RefundResponse,
)
from .money import Amount
from .validators import validate_mbway_phone, validate_payment_id

__all__ = ["AsyncSIBSClient"]


class AsyncSIBSClient:
    """Asynchronous client for the SIBS Gateway API.

    Use as an async context manager to ensure the connection pool is closed::

        async with AsyncSIBSClient(api_key=..., terminal_id=...) as client:
            await client.create_payment(...)
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
        transport: httpx.AsyncBaseTransport | None = None,
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
        self._http = AsyncHTTPClient(
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
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> AsyncSIBSClient:
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
        return self._config.environment is SIBSEnvironment.PRODUCTION

    def _idempotency_headers(self, key: str | None) -> dict[str, str]:
        return build_idempotency_headers(key, self._idempotency_header)

    async def create_payment(
        self,
        *,
        amount: Amount,
        currency: str = "EUR",
        merchant_transaction_id: str,
        transaction_type: str | TransactionType = TransactionType.PURCHASE,
        description: str | None = None,
        return_url: str | None = None,
        cancel_url: str | None = None,
        payment_methods: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentResponse:
        request = P.prepare_payment_request(
            amount=amount,
            currency=currency,
            merchant_transaction_id=merchant_transaction_id,
            transaction_type=transaction_type,
            description=description,
            return_url=return_url,
            cancel_url=cancel_url,
            payment_methods=payment_methods,
            require_https=self._require_https,
        )
        payload = P.build_create_payment_payload(request, self._config.terminal_id)
        data = await self._http.request(
            "POST", "/payments", json=payload, headers=self._idempotency_headers(idempotency_key)
        )
        return P.parse_create_payment_response(data)

    async def pay_with_mbway(
        self,
        *,
        payment_id: str,
        transaction_signature: str,
        customer_phone: str,
        idempotency_key: str | None = None,
    ) -> MBWayResponse:
        """Trigger an MB WAY purchase on a previously created payment.

        See :meth:`pysibs.client.SIBSClient.pay_with_mbway` for details. This call
        authenticates with ``Authorization: Digest`` rather than the bearer token.
        """
        pid = validate_payment_id(payment_id)
        if not transaction_signature or not str(transaction_signature).strip():
            raise SIBSValidationError("transaction_signature is required for MB WAY.")
        phone = validate_mbway_phone(customer_phone)
        headers = {"Authorization": f"Digest {transaction_signature.strip()}"}
        headers.update(self._idempotency_headers(idempotency_key))
        data = await self._http.request(
            "POST",
            f"/payments/{pid}/mbway-id/purchase",
            json=P.build_mbway_payload(phone),
            headers=headers,
        )
        return P.parse_mbway_response(data, pid)

    async def get_payment_status(self, payment_id: str) -> PaymentStatusResponse:
        pid = validate_payment_id(payment_id)
        data = await self._http.request("GET", f"/payments/{pid}/status")
        return P.parse_status_response(data, pid)

    async def refund_payment(
        self,
        *,
        payment_id: str,
        amount: Amount | None = None,
        currency: str = "EUR",
        merchant_refund_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> RefundResponse:
        request = P.prepare_refund_request(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            merchant_refund_id=merchant_refund_id,
        )
        payload = P.build_refund_payload(request)
        data = await self._http.request(
            "POST",
            f"/payments/{request.payment_id}/refund",
            json=payload,
            headers=self._idempotency_headers(idempotency_key),
        )
        return P.parse_refund_response(data, request.payment_id)

    async def capture_payment(
        self,
        *,
        payment_id: str,
        amount: Amount | None = None,
        currency: str = "EUR",
        idempotency_key: str | None = None,
    ) -> OperationResponse:
        request = P.prepare_refund_request(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            merchant_refund_id=None,
        )
        payload = P.build_refund_payload(request)
        data = await self._http.request(
            "POST",
            f"/payments/{request.payment_id}/capture",
            json=payload,
            headers=self._idempotency_headers(idempotency_key),
        )
        return P.parse_operation_response(data, request.payment_id)

    async def cancel_payment(
        self, payment_id: str, *, idempotency_key: str | None = None
    ) -> OperationResponse:
        pid = validate_payment_id(payment_id)
        data = await self._http.request(
            "POST",
            f"/payments/{pid}/cancellation",
            json={},
            headers=self._idempotency_headers(idempotency_key),
        )
        return P.parse_operation_response(data, pid)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncSIBSClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
