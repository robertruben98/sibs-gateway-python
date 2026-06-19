from __future__ import annotations

import pytest

from pysibs import PaymentStatus, normalize_payment_status


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Success", PaymentStatus.CAPTURED),
        ("paid", PaymentStatus.CAPTURED),
        ("AUTHORIZED", PaymentStatus.AUTHORIZED),
        ("pending", PaymentStatus.PENDING),
        ("Declined", PaymentStatus.DECLINED),
        ("cancelled", PaymentStatus.CANCELED),
        ("refunded", PaymentStatus.REFUNDED),
        ("partially_refunded", PaymentStatus.PARTIALLY_REFUNDED),
        ("expired", PaymentStatus.EXPIRED),
        ("000", PaymentStatus.CAPTURED),
    ],
)
def test_normalize_known_status(raw: str, expected: PaymentStatus) -> None:
    assert normalize_payment_status(raw) == expected


@pytest.mark.parametrize("raw", ["something_new", "", "   ", None])
def test_normalize_unknown_status(raw: str | None) -> None:
    assert normalize_payment_status(raw) == PaymentStatus.UNKNOWN
