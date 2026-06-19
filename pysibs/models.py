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
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatusResponse",
    "RefundRequest",
    "RefundResponse",
    "OperationResponse",
    "WebhookEvent",
]


class PaymentRequest(BaseModel):
    """Validated input for creating a payment."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    currency: str
    merchant_transaction_id: str
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
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PaymentStatusResponse(BaseModel):
    """Result of querying a payment's status."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    payment_id: str
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
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


class WebhookEvent(BaseModel):
    """A parsed (and optionally verified) webhook notification."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_type: str | None = None
    payment_id: str | None = None
    merchant_transaction_id: str | None = None
    status: PaymentStatus = PaymentStatus.UNKNOWN
    raw_status: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
