"""Money handling utilities.

Money is always represented internally as :class:`decimal.Decimal`. Floats are
rejected outright: passing a ``float`` is almost always a bug because binary floating
point cannot represent most decimal monetary values exactly (``0.1 + 0.2`` is the
classic example). Callers should pass amounts as ``str``, ``int`` or ``Decimal``.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .exceptions import SIBSValidationError

__all__ = ["Amount", "normalize_amount", "format_amount"]

# Currencies that use a different number of minor-unit decimal places than 2.
# Most currencies (EUR, USD, GBP...) use 2. This table only lists exceptions.
_CURRENCY_DECIMALS: dict[str, int] = {
    "JPY": 0,
    "KRW": 0,
    "CLP": 0,
    "ISK": 0,
    "BHD": 3,
    "KWD": 3,
    "OMR": 3,
    "TND": 3,
}
_DEFAULT_DECIMALS = 2

# An ``Amount`` is anything we accept from the caller as a monetary value.
Amount = str | int | Decimal


def _decimals_for_currency(currency: str | None) -> int:
    if currency is None:
        return _DEFAULT_DECIMALS
    return _CURRENCY_DECIMALS.get(currency.strip().upper(), _DEFAULT_DECIMALS)


def normalize_amount(value: Amount, currency: str | None = "EUR") -> Decimal:
    """Normalize an amount to a :class:`Decimal` quantized for ``currency``.

    Accepts ``str``, ``int`` or ``Decimal``. Rejects ``float`` and ``bool`` with a
    :class:`SIBSValidationError`. The result is quantized to the number of decimal
    places appropriate for the currency (2 for EUR) using round-half-up, and must be
    strictly greater than zero.
    """
    # ``bool`` is a subclass of ``int`` -- reject it explicitly to avoid surprises.
    if isinstance(value, bool):
        raise SIBSValidationError("Amount must not be a boolean.")

    if isinstance(value, float):
        raise SIBSValidationError(
            "Amount must not be a float (use str, int or Decimal to avoid rounding "
            f"errors); got {value!r}."
        )

    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, int):
        amount = Decimal(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise SIBSValidationError("Amount string must not be empty.")
        try:
            amount = Decimal(stripped)
        except InvalidOperation as exc:
            raise SIBSValidationError(f"Amount {value!r} is not a valid number.") from exc
    else:
        raise SIBSValidationError(
            f"Amount must be a str, int or Decimal; got {type(value).__name__}."
        )

    if not amount.is_finite():
        raise SIBSValidationError(f"Amount must be finite; got {value!r}.")

    decimals = _decimals_for_currency(currency)
    quantum = Decimal(1).scaleb(-decimals)
    try:
        quantized = amount.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:  # pragma: no cover - extreme precision overflow
        raise SIBSValidationError(f"Amount {value!r} cannot be represented.") from exc

    if quantized <= 0:
        raise SIBSValidationError(f"Amount must be greater than zero; got {value!r}.")

    return quantized


def format_amount(value: Amount, currency: str | None = "EUR") -> str:
    """Normalize and render an amount as a fixed-point string (e.g. ``"25.50"``)."""
    return f"{normalize_amount(value, currency):f}"
