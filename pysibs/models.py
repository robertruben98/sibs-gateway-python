"""Typed request/response models.

Response models always expose ``raw_response`` (or ``raw_payload`` for webhooks) so
callers can reach any SIBS field that PySIBS has not (yet) normalized. This is a
deliberate design choice: the normalized surface stays small and stable, while no
information from SIBS is ever lost.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import PaymentStatus

__all__ = [
    "PaymentReference",
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatusResponse",
    "RefundRequest",
    "RefundResponse",
    "OperationResponse",
    "MBWayResponse",
    "ActionResponse",
    "CardPaymentResponse",
    "WebhookEvent",
]


class ActionResponse(BaseModel):
    """A follow-up action SIBS asks the merchant to perform.

    For card payments this carries the 3D-Secure redirect: the shopper's browser must
    be sent (usually via an auto-submitting POST form) to ``url`` with ``params`` as
    form fields. See :func:`pysibs.threeds.build_3ds_redirect`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: str | None = None
    method: str = "POST"
    url: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class PaymentReference(BaseModel):
    """A MULTIBANCO reference returned by SIBS (entity + reference the shopper pays)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    entity: str | None = None
    reference: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    expire_date: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class PaymentRequest(BaseModel):
    """Validated input for creating a payment."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    currency: str
    merchant_transaction_id: str
    transaction_type: str = "PURS"
    description: str | None = None
    return_url: str | None = None
    cancel_url: str | None = None
    payment_methods: list[str] | None = None


class PaymentResponse(BaseModel):
    """Result of creating a payment."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str | None = None
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    redirect_url: str | None = None
    signature: str | None = None
    payment_reference: PaymentReference | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PaymentStatusResponse(BaseModel):
    """Result of querying a payment's status."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    payment_id: str
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    payment_reference: PaymentReference | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class RefundRequest(BaseModel):
    """Validated input for refunding a payment."""

    model_config = ConfigDict(extra="forbid")

    payment_id: str
    amount: Decimal | None = None
    currency: str = "EUR"
    merchant_refund_id: str | None = None


class RefundResponse(BaseModel):
    """Result of a refund operation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str | None = None
    payment_id: str
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class OperationResponse(BaseModel):
    """Generic result for capture / cancel operations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    payment_id: str
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class MBWayResponse(BaseModel):
    """Result of triggering an MB WAY purchase on a created payment."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    payment_id: str
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class CardPaymentResponse(BaseModel):
    """Result of submitting a card payment.

    When ``status`` is :attr:`PaymentStatus.ACTION_REQUIRED` (SIBS ``"Partial"``), a 3DS
    authentication is required: inspect ``action`` for the redirect details and resubmit
    the payment afterwards.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    payment_id: str
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    action: ActionResponse | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)

    @property
    def requires_3ds(self) -> bool:
        """True when a 3D-Secure authentication step is required."""
        return self.status is PaymentStatus.ACTION_REQUIRED or self.action is not None


class WebhookEvent(BaseModel):
    """A parsed (and decrypted) webhook notification.

    ``notification_id`` must be echoed back in the HTTP 200 acknowledgement so SIBS
    does not retry the notification (see :func:`pysibs.webhooks.build_acknowledgement`).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_type: str | None = None
    notification_id: str | None = None
    payment_id: str | None = None
    merchant_transaction_id: str | None = None
    payment_method: str | None = None
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    payment_reference: PaymentReference | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
