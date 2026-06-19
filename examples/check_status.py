"""Check the status of a payment."""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from pysibs import SIBSClient

load_dotenv()


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python examples/check_status.py <payment_id>")
        raise SystemExit(2)

    client = SIBSClient.from_env()
    status = client.get_payment_status(sys.argv[1])
    print("payment_id:", status.payment_id)
    print("status:    ", status.status)
    print("raw_status:", status.raw_status)
    client.close()


if __name__ == "__main__":
    main()
