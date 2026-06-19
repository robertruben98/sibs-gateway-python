from __future__ import annotations

import pytest

from pysibs import SIBSValidationError
from pysibs.validators import (
    validate_currency,
    validate_merchant_transaction_id,
    validate_payment_id,
    validate_terminal_id,
    validate_url,
)


def test_validate_currency_upper() -> None:
    assert validate_currency("eur") == "EUR"


@pytest.mark.parametrize("value", ["", "EU", "EURO", "12$", "  "])
def test_validate_currency_invalid(value: str) -> None:
    with pytest.raises(SIBSValidationError):
        validate_currency(value)


def test_validate_merchant_transaction_id() -> None:
    assert validate_merchant_transaction_id(" ORD-1 ") == "ORD-1"


def test_validate_merchant_transaction_id_empty() -> None:
    with pytest.raises(SIBSValidationError):
        validate_merchant_transaction_id("")


def test_validate_payment_id_empty() -> None:
    with pytest.raises(SIBSValidationError):
        validate_payment_id("   ")


def test_validate_terminal_id_empty() -> None:
    with pytest.raises(SIBSValidationError):
        validate_terminal_id("")


def test_validate_url_https() -> None:
    assert validate_url("https://x.test/ok") == "https://x.test/ok"


def test_validate_url_requires_https() -> None:
    with pytest.raises(SIBSValidationError):
        validate_url("http://x.test/no")


def test_validate_url_allows_http_when_not_required() -> None:
    assert validate_url("http://x.test/ok", require_https=False) == "http://x.test/ok"
