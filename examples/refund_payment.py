"""Refund a payment (full or partial)."""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from pysibs import SIBSClient

load_dotenv()


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python examples/refund_payment.py <payment_id> [amount]")
        raise SystemExit(2)

    payment_id = sys.argv[1]
    amount = sys.argv[2] if len(sys.argv) > 2 else None  # None => full refund

    client = SIBSClient.from_env()
    refund = client.refund_payment(
        payment_id=payment_id,
        amount=amount,
        merchant_refund_id=f"REF-{payment_id}",
    )
    print("refund id:", refund.id)
    print("status:   ", refund.status)
    client.close()


if __name__ == "__main__":
    main()
