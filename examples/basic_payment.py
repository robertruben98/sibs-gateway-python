"""Create a payment.

Run with sandbox credentials in your environment (or a local .env):

    pip install "pysibs[examples]"
    python examples/basic_payment.py
"""

from __future__ import annotations

from dotenv import load_dotenv

from pysibs import SIBSClient

load_dotenv()  # examples may use .env; the core library never does.


def main() -> None:
    client = SIBSClient.from_env()
    payment = client.create_payment(
        amount="10.00",
        currency="EUR",
        merchant_transaction_id="ORDER-123",
        return_url="https://example.com/payment/success",
        cancel_url="https://example.com/payment/cancel",
        payment_methods=["CARD", "MBWAY", "MULTIBANCO"],
    )
    print("id:          ", payment.id)
    print("status:      ", payment.status)
    print("redirect_url:", payment.redirect_url)
    client.close()


if __name__ == "__main__":
    main()
