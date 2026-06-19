"""3D-Secure helpers for card payments.

When a card payment returns ``paymentStatus: "Partial"``, SIBS includes an
``actionResponse`` describing where to send the shopper's browser to complete the 3DS
challenge. The browser must be POSTed to ``action.url`` with ``action.params`` as form
fields; after the challenge the shopper is redirected back and the payment is resubmitted.

These helpers turn the typed :class:`~pysibs.models.ActionResponse` into something you
can render in a web response. They do not perform any I/O.
"""

from __future__ import annotations

from html import escape
from typing import Any

from .exceptions import SIBSValidationError
from .models import ActionResponse

__all__ = ["build_3ds_redirect", "render_3ds_redirect_html", "build_browser_data"]


def build_browser_data(
    *,
    accept_header: str,
    user_agent: str,
    language: str = "en-US",
    color_depth: int = 24,
    screen_height: int,
    screen_width: int,
    timezone_offset: int = 0,
    java_enabled: bool = False,
) -> dict[str, Any]:
    """Assemble the 3DS browser data collected from the shopper's browser.

    Returns a dict with the ``browser*`` field names SIBS uses. 3DS requires this device
    information; collect the values client-side (the ``Accept``/``User-Agent`` headers
    server-side). Per the official docs, place the result under ``info.deviceInfo`` in the
    ``card/purchase`` request body (the same call as
    :meth:`~pysibs.client.SIBSClient.pay_with_card`) — 3DS is not a separate endpoint.
    For example::

        body = {"cardInfo": {...}, "info": {"deviceInfo": build_browser_data(...)}}
    """
    return {
        "browserAcceptHeader": accept_header,
        "browserUserAgent": user_agent,
        "browserLanguage": language,
        "browserColorDepth": str(color_depth),
        "browserScreenHeight": str(screen_height),
        "browserScreenWidth": str(screen_width),
        "browserTZ": str(timezone_offset),
        "browserJavaEnabled": java_enabled,
    }


def build_3ds_redirect(action: ActionResponse) -> dict[str, Any]:
    """Return the bits needed to redirect the browser for 3DS.

    ``{"method": "POST", "url": ..., "fields": {...}}`` — render these as an
    auto-submitting form (or use :func:`render_3ds_redirect_html`).
    """
    if action.url is None:
        raise SIBSValidationError("ActionResponse has no url to redirect to.")
    return {"method": action.method or "POST", "url": action.url, "fields": dict(action.params)}


def render_3ds_redirect_html(action: ActionResponse, *, auto_submit: bool = True) -> str:
    """Render a self-contained HTML page that POSTs the shopper to the 3DS challenge.

    Return this as the body of your HTTP response when a card payment requires 3DS.
    All values are HTML-escaped.
    """
    redirect = build_3ds_redirect(action)
    inputs = "\n".join(
        f'    <input type="hidden" name="{escape(str(name))}" value="{escape(str(value))}">'
        for name, value in redirect["fields"].items()
    )
    onload = ' onload="document.forms[0].submit()"' if auto_submit else ""
    return (
        "<!DOCTYPE html>\n"
        f"<html>\n<body{onload}>\n"
        f'  <form method="{escape(redirect["method"])}" action="{escape(redirect["url"])}">\n'
        f"{inputs}\n"
        '    <noscript><button type="submit">Continue</button></noscript>\n'
        "  </form>\n"
        "</body>\n</html>"
    )
