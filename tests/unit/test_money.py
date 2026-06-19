from __future__ import annotations

from decimal import Decimal

import pytest

from pysibs import SIBSValidationError, format_amount, normalize_amount


def test_amount_accepts_string() -> None:
    assert normalize_amount("25.50") == Decimal("25.50")


def test_amount_accepts_decimal() -> None:
    assert normalize_amount(Decimal("25.50")) == Decimal("25.50")


def test_amount_accepts_int() -> None:
    assert normalize_amount(10) == Decimal("10.00")


def test_amount_rejects_float() -> None:
    with pytest.raises(SIBSValidationError):
        normalize_amount(25.50)  # type: ignore[arg-type]


def test_amount_rejects_bool() -> None:
    with pytest.raises(SIBSValidationError):
        normalize_amount(True)  # type: ignore[arg-type]


def test_amount_rejects_zero() -> None:
    with pytest.raises(SIBSValidationError):
        normalize_amount("0.00")


def test_amount_rejects_negative() -> None:
    with pytest.raises(SIBSValidationError):
        normalize_amount("-5.00")


def test_amount_rejects_empty_string() -> None:
    with pytest.raises(SIBSValidationError):
        normalize_amount("   ")


def test_amount_rejects_garbage() -> None:
    with pytest.raises(SIBSValidationError):
        normalize_amount("abc")


def test_amount_quantizes_to_two_decimals() -> None:
    assert normalize_amount("25.5") == Decimal("25.50")
    assert normalize_amount("25.005") == Decimal("25.01")  # round half up


def test_amount_jpy_zero_decimals() -> None:
    assert normalize_amount("1000", currency="JPY") == Decimal("1000")


def test_format_amount() -> None:
    assert format_amount("25.5") == "25.50"
    assert format_amount(10) == "10.00"
