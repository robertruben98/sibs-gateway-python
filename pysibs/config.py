"""Environment and client configuration.

The base URLs below follow SIBS' historical naming (a quality/sandbox domain and a
production domain). They are isolated here so they can be confirmed against the
current official documentation and adjusted in one place. Callers may also override
``base_url`` explicitly when constructing the client, which bypasses this table
entirely (useful for mocks, proxies, or a future endpoint change).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

import httpx

from .exceptions import SIBSConfigurationError, SIBSValidationError
from .validators import validate_terminal_id

__all__ = ["SIBSEnvironment", "ClientConfig", "BASE_URLS", "DEFAULT_TIMEOUT"]


class SIBSEnvironment(str, Enum):
    """Supported SIBS environments."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"

    @classmethod
    def coerce(cls, value: str | SIBSEnvironment) -> SIBSEnvironment:
        """Coerce a string (case-insensitive) or enum member into an environment.

        Raises :class:`SIBSConfigurationError` for unknown values.
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            valid = ", ".join(member.value for member in cls)
            raise SIBSConfigurationError(
                f"Invalid environment {value!r}; expected one of: {valid}."
            ) from exc


# NOTE: confirm against the current official SIBS documentation before publishing.
# The quality/sandbox and production hosts. Note SIBS exposes (at least) two test hosts:
# the contracted *quality* host below, and the free Developer Portal sandbox at
# ``https://sandbox.sibspayments.com/sibs/spg/v2`` (no certificate/contract; the swagger
# confirms this host + the ``/sibs/spg/v2`` prefix). If you registered on
# developer.sibsapimarket.com, pass ``base_url="https://sandbox.sibspayments.com/sibs/spg/v2"``.
BASE_URLS: dict[SIBSEnvironment, str] = {
    SIBSEnvironment.SANDBOX: "https://api.qly.sibspayments.com/sibs/spg/v2",
    SIBSEnvironment.PRODUCTION: "https://api.sibspayments.com/sibs/spg/v2",
}

DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class ClientConfig:
    """Resolved, validated configuration for a :class:`~pysibs.client.SIBSClient`."""

    api_key: str
    terminal_id: str
    environment: SIBSEnvironment
    base_url: str
    timeout: float | httpx.Timeout
    client_id: str | None = None
    webhook_secret: str | None = None

    @classmethod
    def create(
        cls,
        *,
        api_key: str,
        terminal_id: str,
        environment: str | SIBSEnvironment = SIBSEnvironment.SANDBOX,
        base_url: str | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        client_id: str | None = None,
        webhook_secret: str | None = None,
    ) -> ClientConfig:
        if not api_key or not str(api_key).strip():
            raise SIBSConfigurationError("api_key is required.")

        try:
            terminal = validate_terminal_id(terminal_id)
        except SIBSValidationError as exc:
            raise SIBSConfigurationError(str(exc)) from exc
        env = SIBSEnvironment.coerce(environment)
        resolved_base_url = (base_url or BASE_URLS[env]).rstrip("/")

        # A plain number is treated as a total-seconds timeout; an httpx.Timeout gives
        # granular connect/read/write/pool control and is passed through untouched.
        if isinstance(timeout, httpx.Timeout):
            resolved_timeout: float | httpx.Timeout = timeout
        else:
            if timeout <= 0:
                raise SIBSConfigurationError("timeout must be a positive number of seconds.")
            resolved_timeout = float(timeout)

        return cls(
            api_key=str(api_key).strip(),
            terminal_id=terminal,
            environment=env,
            base_url=resolved_base_url,
            timeout=resolved_timeout,
            client_id=(
                client_id.strip() if isinstance(client_id, str) and client_id.strip() else None
            ),
            webhook_secret=webhook_secret or None,
        )

    @classmethod
    def from_env(
        cls,
        *,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        base_url: str | None = None,
    ) -> ClientConfig:
        """Build configuration from ``SIBS_*`` environment variables.

        Reads ``SIBS_API_KEY``, ``SIBS_TERMINAL_ID``, ``SIBS_ENVIRONMENT``
        (defaults to ``sandbox``), and optionally ``SIBS_CLIENT_ID`` and
        ``SIBS_WEBHOOK_SECRET``.
        """
        api_key = os.environ.get("SIBS_API_KEY")
        terminal_id = os.environ.get("SIBS_TERMINAL_ID")
        if not api_key:
            raise SIBSConfigurationError("SIBS_API_KEY environment variable is not set.")
        if not terminal_id:
            raise SIBSConfigurationError("SIBS_TERMINAL_ID environment variable is not set.")

        return cls.create(
            api_key=api_key,
            terminal_id=terminal_id,
            environment=os.environ.get("SIBS_ENVIRONMENT", SIBSEnvironment.SANDBOX.value),
            base_url=base_url,
            timeout=timeout,
            client_id=os.environ.get("SIBS_CLIENT_ID"),
            webhook_secret=os.environ.get("SIBS_WEBHOOK_SECRET"),
        )
