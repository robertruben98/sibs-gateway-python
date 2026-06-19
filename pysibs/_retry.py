"""Retry policy for the HTTP transport.

Payments are sensitive: blindly retrying a non-idempotent ``POST`` could double-charge a
shopper. The defaults here are therefore conservative:

* **Idempotent methods** (``GET`` by default) are retried on connection errors,
  timeouts and retryable status codes.
* **Non-idempotent methods** (``POST`` …) are retried **only** on status codes that
  guarantee the request was not processed -- ``429 Too Many Requests`` and
  ``503 Service Unavailable`` -- never on timeouts or connection errors.

Backoff is exponential with full jitter, capped at ``max_backoff``; a server-provided
``Retry-After`` header takes precedence when present.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

__all__ = ["RetryConfig", "coerce_retries"]

# Statuses that are always safe to retry because the request was not processed.
_ALWAYS_SAFE_STATUSES = frozenset({429, 503})


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for automatic retries.

    ``max_retries`` is the number of *additional* attempts after the first try (so
    ``max_retries=2`` means up to 3 requests). Set it to ``0`` to disable retries.
    """

    max_retries: int = 2
    backoff_factor: float = 0.5
    max_backoff: float = 30.0
    jitter: bool = True
    retry_statuses: frozenset[int] = frozenset({429, 502, 503, 504})
    idempotent_methods: frozenset[str] = field(
        default_factory=lambda: frozenset({"GET", "HEAD", "OPTIONS"})
    )
    respect_retry_after: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.backoff_factor < 0 or self.max_backoff < 0:
            raise ValueError("backoff values must be >= 0")

    def _is_idempotent(self, method: str) -> bool:
        return method.upper() in self.idempotent_methods

    def should_retry_status(self, method: str, status: int, attempt: int) -> bool:
        """Whether to retry given an HTTP status on attempt ``attempt`` (0-based)."""
        if attempt >= self.max_retries:
            return False
        if status in _ALWAYS_SAFE_STATUSES:
            return True
        return status in self.retry_statuses and self._is_idempotent(method)

    def should_retry_exception(self, method: str, attempt: int) -> bool:
        """Whether to retry a connection/timeout error. Idempotent methods only."""
        if attempt >= self.max_retries:
            return False
        return self._is_idempotent(method)

    def backoff(self, attempt: int, retry_after: float | None = None) -> float:
        """Seconds to sleep before the next attempt (``attempt`` is 0-based)."""
        if retry_after is not None and self.respect_retry_after:
            return max(0.0, min(retry_after, self.max_backoff))
        base: float = min(self.backoff_factor * (2**attempt), self.max_backoff)
        if self.jitter:
            return random.uniform(0.0, base)
        return base


def coerce_retries(retries: RetryConfig | int | None) -> RetryConfig:
    """Normalize the ``retries`` argument into a :class:`RetryConfig`.

    ``None`` -> defaults; an ``int`` -> that many retries with default backoff.
    """
    if retries is None:
        return RetryConfig()
    if isinstance(retries, int):
        return RetryConfig(max_retries=retries)
    return retries


def retry_after_seconds(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header value (delta-seconds or HTTP date)."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = (when - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delta)
