"""Internal HTTP transport built on httpx.

This module centralises every network concern so the rest of the library never
touches ``httpx`` directly:

* default headers (auth, content type) are built once;
* the API key is sent in the ``Authorization`` header and is never logged or placed
  into exception messages/bodies;
* every ``httpx`` error is translated into a PySIBS exception;
* JSON parsing and HTTP-status-to-exception mapping live in one place and are shared
  between the sync and async clients;
* retries with backoff (see :mod:`pysibs._retry`) and credential-safe debug logging
  are applied uniformly.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ._retry import RetryConfig, retry_after_seconds
from ._version import __version__
from .exceptions import (
    SIBSAPIError,
    SIBSAuthenticationError,
    SIBSConnectionError,
    SIBSRateLimitError,
    SIBSTimeoutError,
)

__all__ = ["HTTPClient", "AsyncHTTPClient"]

JSONDict = dict[str, Any]

# Library logger. PySIBS never attaches a handler; configure logging in your app to see
# these DEBUG records. Records carry method/path/status/attempt/elapsed only -- never
# headers, bodies or credentials.
logger = logging.getLogger("pysibs")


def _build_default_headers(api_key: str, client_id: str | None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"pysibs/{__version__}",
    }
    if client_id:
        # SIBS' API gateway commonly requires a client id header in addition to the
        # bearer token. It is optional here so the library works without it too.
        headers["X-IBM-Client-Id"] = client_id
    return headers


def _parse_json(response: httpx.Response) -> JSONDict | str:
    """Best-effort parse of a response body as a JSON object.

    Returns the parsed dict, or the raw text if the body is not a JSON object.
    Never raises.
    """
    try:
        data = response.json()
    except (ValueError, UnicodeDecodeError):
        return response.text
    if isinstance(data, dict):
        return data
    return {"data": data} if data is not None else {}


def _map_status_error(response: httpx.Response) -> Exception:
    """Map a non-2xx HTTP response onto the appropriate PySIBS exception.

    The response body is parsed best-effort and attached, but the request payload
    (which may contain credentials) is never included.
    """
    status = response.status_code
    body = _parse_json(response)

    if status in (401, 403):
        return SIBSAuthenticationError(
            "SIBS rejected the credentials (authentication/authorization failed)."
        )
    if status == 408:
        return SIBSTimeoutError("SIBS API returned HTTP 408 (request timeout).")
    if status == 429:
        return SIBSRateLimitError(
            "SIBS API rate limit exceeded (HTTP 429).",
            status_code=429,
            response_body=body,
            retry_after=retry_after_seconds(response.headers.get("Retry-After")),
        )

    return SIBSAPIError(
        f"SIBS API request failed with HTTP {status}.",
        status_code=status,
        response_body=body,
    )


def _check_response(response: httpx.Response) -> JSONDict:
    """Raise on error responses, otherwise return the parsed JSON object."""
    if response.is_success:
        parsed = _parse_json(response)
        if isinstance(parsed, dict):
            return parsed
        # A successful response with a non-object body is unexpected but harmless;
        # wrap it so callers always get a dict in ``raw_response``.
        return {"data": parsed}
    raise _map_status_error(response)


class HTTPClient:
    """Synchronous HTTP client wrapping :class:`httpx.Client`."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        client_id: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        retries: RetryConfig | None = None,
        verify: bool | str = True,
        proxy: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._retries = retries if retries is not None else RetryConfig()
        self._client = httpx.Client(
            base_url=base_url,
            headers=_build_default_headers(api_key, client_id),
            timeout=timeout,
            verify=verify,
            proxy=proxy,
            transport=transport,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json: JSONDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> JSONDict:
        attempt = 0
        while True:
            started = time.monotonic()
            try:
                response = self._client.request(method, path, json=json, headers=headers)
            except httpx.TimeoutException as exc:
                if self._retries.should_retry_exception(method, attempt):
                    _log_retry(method, path, attempt, reason="timeout")
                    time.sleep(self._retries.backoff(attempt))
                    attempt += 1
                    continue
                raise SIBSTimeoutError(f"Request to SIBS timed out: {exc!s}") from exc
            except httpx.TransportError as exc:
                if self._retries.should_retry_exception(method, attempt):
                    _log_retry(method, path, attempt, reason="connection")
                    time.sleep(self._retries.backoff(attempt))
                    attempt += 1
                    continue
                raise SIBSConnectionError(f"Could not connect to SIBS: {exc!s}") from exc

            _log_response(method, path, response.status_code, started, attempt)
            if not response.is_success and self._retries.should_retry_status(
                method, response.status_code, attempt
            ):
                retry_after = retry_after_seconds(response.headers.get("Retry-After"))
                _log_retry(method, path, attempt, reason=f"status {response.status_code}")
                time.sleep(self._retries.backoff(attempt, retry_after))
                attempt += 1
                continue
            return _check_response(response)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class AsyncHTTPClient:
    """Asynchronous HTTP client wrapping :class:`httpx.AsyncClient`."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        client_id: str | None = None,
        timeout: float | httpx.Timeout = 30.0,
        retries: RetryConfig | None = None,
        verify: bool | str = True,
        proxy: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._retries = retries if retries is not None else RetryConfig()
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=_build_default_headers(api_key, client_id),
            timeout=timeout,
            verify=verify,
            proxy=proxy,
            transport=transport,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: JSONDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> JSONDict:
        import asyncio

        attempt = 0
        while True:
            started = time.monotonic()
            try:
                response = await self._client.request(method, path, json=json, headers=headers)
            except httpx.TimeoutException as exc:
                if self._retries.should_retry_exception(method, attempt):
                    _log_retry(method, path, attempt, reason="timeout")
                    await asyncio.sleep(self._retries.backoff(attempt))
                    attempt += 1
                    continue
                raise SIBSTimeoutError(f"Request to SIBS timed out: {exc!s}") from exc
            except httpx.TransportError as exc:
                if self._retries.should_retry_exception(method, attempt):
                    _log_retry(method, path, attempt, reason="connection")
                    await asyncio.sleep(self._retries.backoff(attempt))
                    attempt += 1
                    continue
                raise SIBSConnectionError(f"Could not connect to SIBS: {exc!s}") from exc

            _log_response(method, path, response.status_code, started, attempt)
            if not response.is_success and self._retries.should_retry_status(
                method, response.status_code, attempt
            ):
                retry_after = retry_after_seconds(response.headers.get("Retry-After"))
                _log_retry(method, path, attempt, reason=f"status {response.status_code}")
                await asyncio.sleep(self._retries.backoff(attempt, retry_after))
                attempt += 1
                continue
            return _check_response(response)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncHTTPClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


def _log_response(method: str, path: str, status: int, started: float, attempt: int) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.debug(
            "SIBS %s %s -> %s (%.0fms, attempt %d)", method, path, status, elapsed_ms, attempt + 1
        )


def _log_retry(method: str, path: str, attempt: int, *, reason: str) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("SIBS %s %s retrying after %s (attempt %d)", method, path, reason, attempt + 1)
