"""Integration tests against a real SIBS sandbox.

These are disabled by default (the ``integration`` marker is excluded in
``pyproject.toml``). They require real sandbox credentials in the environment and are
meant to be run manually:

    pytest -m integration

They are intentionally light and tolerant: the goal is to confirm connectivity and
that responses can be parsed, not to assert on exact sandbox behaviour.
"""

from __future__ import annotations

import os

import pytest

from pysibs import SIBSClient

pytestmark = pytest.mark.integration


@pytest.fixture()
def sandbox_client() -> SIBSClient:
    if not os.environ.get("SIBS_API_KEY") or not os.environ.get("SIBS_TERMINAL_ID"):
        pytest.skip("SIBS sandbox credentials not configured")
    client = SIBSClient.from_env()
    try:
        yield client
    finally:
        client.close()


def test_create_payment_sandbox(sandbox_client: SIBSClient) -> None:
    payment = sandbox_client.create_payment(
        amount="1.00",
        currency="EUR",
        merchant_transaction_id="PYSIBS-IT-0001",
    )
    assert payment.raw_response is not None
