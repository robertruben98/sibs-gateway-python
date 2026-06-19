"""PySIBS -- a modern Python SDK for SIBS Gateway payment integrations.

Typical usage::

    from pysibs import SIBSClient

    client = SIBSClient(api_key="...", terminal_id="...", environment="sandbox")
    payment = client.create_payment(
        amount="25.50",
        currency="EUR",
        merchant_transaction_id="ORD-1001",
    )
    print(payment.status, payment.redirect_url)
"""

from __future__ import annotations

from ._version import __version__
from .async_client import AsyncSIBSClient
from .client import SIBSClient
from .config import BASE_URLS, ClientConfig, SIBSEnvironment
from .enums import PaymentMethod, PaymentStatus, normalize_payment_status
from .exceptions import (
    SIBSAPIError,
    SIBSAuthenticationError,
    SIBSConfigurationError,
    SIBSConnectionError,
    SIBSError,
    SIBSInvalidWebhookSignature,
    SIBSTimeoutError,
    SIBSValidationError,
)
from .models import (
    OperationResponse,
    PaymentRequest,
    PaymentResponse,
    PaymentStatusResponse,
    RefundRequest,
    RefundResponse,
    WebhookEvent,
)
from .money import format_amount, normalize_amount
from .webhooks import (
    hmac_sha256_verifier,
    parse_webhook,
    verify_webhook_signature,
)

__all__ = [
    "__version__",
    # Clients
    "SIBSClient",
    "AsyncSIBSClient",
    # Config
    "SIBSEnvironment",
    "ClientConfig",
    "BASE_URLS",
    # Enums / status
    "PaymentStatus",
    "PaymentMethod",
    "normalize_payment_status",
    # Models
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatusResponse",
    "RefundRequest",
    "RefundResponse",
    "OperationResponse",
    "WebhookEvent",
    # Money
    "normalize_amount",
    "format_amount",
    # Webhooks
    "parse_webhook",
    "verify_webhook_signature",
    "hmac_sha256_verifier",
    # Exceptions
    "SIBSError",
    "SIBSConfigurationError",
    "SIBSValidationError",
    "SIBSAuthenticationError",
    "SIBSAPIError",
    "SIBSTimeoutError",
    "SIBSConnectionError",
    "SIBSInvalidWebhookSignature",
]
