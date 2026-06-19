"""Exception hierarchy for PySIBS.

All exceptions raised by this library inherit from :class:`SIBSError`, so callers
can catch a single base class if they want to treat every PySIBS failure the same
way, or catch a more specific subclass when they need finer control.

The library never lets raw ``httpx`` exceptions escape to the caller; they are
always translated into one of the exceptions defined here.
"""

from __future__ import annotations

from typing import Any

__all__ = [
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


class SIBSError(Exception):
    """Base class for every exception raised by PySIBS."""


class SIBSConfigurationError(SIBSError):
    """Raised when the client is misconfigured (missing credentials, bad env...)."""


class SIBSValidationError(SIBSError):
    """Raised when user-supplied input fails validation before hitting the API."""


class SIBSAuthenticationError(SIBSError):
    """Raised when SIBS rejects the credentials (HTTP 401 / 403)."""


class SIBSAPIError(SIBSError):
    """Raised when SIBS returns an error response we cannot map to anything more specific.

    The HTTP status code and the (best-effort parsed) response body are attached so
    callers can inspect them. Note that ``response_body`` never contains the request
    payload, so credentials are not leaked through this exception.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code is not None:
            return f"{self.message} (status_code={self.status_code})"
        return self.message


class SIBSRateLimitError(SIBSAPIError):
    """Raised when SIBS returns HTTP 429 (too many requests).

    Subclasses :class:`SIBSAPIError` for backwards compatibility. ``retry_after`` is the
    number of seconds the server asked us to wait (from the ``Retry-After`` header), if
    provided.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = 429,
        response_body: dict[str, Any] | str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.retry_after = retry_after


class SIBSTimeoutError(SIBSError):
    """Raised when a request to SIBS times out (connect/read/write)."""


class SIBSConnectionError(SIBSError):
    """Raised when we cannot reach SIBS at all (DNS, TCP, TLS...)."""


class SIBSInvalidWebhookSignature(SIBSError):
    """Raised when a webhook payload fails signature verification."""
