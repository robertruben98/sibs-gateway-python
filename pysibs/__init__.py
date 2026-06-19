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

from ._retry import RetryConfig
from ._version import __version__
from .async_client import AsyncSIBSClient
from .client import SIBSClient
from .config import BASE_URLS, ClientConfig, SIBSEnvironment
from .enums import (
    PaymentMethod,
    PaymentStatus,
    TransactionType,
    normalize_payment_status,
)
from .exceptions import (
    SIBSAPIError,
    SIBSAuthenticationError,
    SIBSConfigurationError,
    SIBSConnectionError,
    SIBSError,
    SIBSInvalidWebhookSignature,
    SIBSRateLimitError,
    SIBSTimeoutError,
    SIBSValidationError,
)
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
    WebhookEvent,
)
from .money import format_amount, normalize_amount
from .redaction import mask_pan, redact
from .threeds import build_3ds_redirect, build_browser_data, render_3ds_redirect_html
from .webhooks import (
    NotificationDeduplicator,
    build_acknowledgement,
    decrypt_webhook,
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
    "RetryConfig",
    "BASE_URLS",
    # Enums / status
    "PaymentStatus",
    "PaymentMethod",
    "TransactionType",
    "normalize_payment_status",
    # Models
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatusResponse",
    "PaymentReference",
    "RefundRequest",
    "RefundResponse",
    "OperationResponse",
    "MBWayResponse",
    "ActionResponse",
    "CardToken",
    "CardPaymentResponse",
    "WebhookEvent",
    # Money
    "normalize_amount",
    "format_amount",
    # 3D-Secure
    "build_3ds_redirect",
    "render_3ds_redirect_html",
    "build_browser_data",
    # Webhooks
    "decrypt_webhook",
    "parse_webhook",
    "build_acknowledgement",
    "NotificationDeduplicator",
    "verify_webhook_signature",
    "hmac_sha256_verifier",
    # Observability / redaction
    "mask_pan",
    "redact",
    # Exceptions
    "SIBSError",
    "SIBSConfigurationError",
    "SIBSValidationError",
    "SIBSAuthenticationError",
    "SIBSAPIError",
    "SIBSRateLimitError",
    "SIBSTimeoutError",
    "SIBSConnectionError",
    "SIBSInvalidWebhookSignature",
]
