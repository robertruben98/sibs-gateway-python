"""Shared pytest fixtures.

Tests never talk to a real SIBS environment. The ``client`` fixture builds a
:class:`SIBSClient` whose HTTP layer is intercepted by ``respx`` (mounted against a
deterministic ``base_url``). Credentials here are obviously fake.
"""

from __future__ import annotations

import pytest

from pysibs import SIBSClient

TEST_BASE_URL = "https://sibs.test/sibs/spg/v2"


@pytest.fixture()
def base_url() -> str:
    return TEST_BASE_URL


@pytest.fixture()
def client() -> SIBSClient:
    sibs = SIBSClient(
        api_key="test_api_key",
        terminal_id="123456",
        environment="sandbox",
        base_url=TEST_BASE_URL,
        client_id="test-client-id",
    )
    try:
        yield sibs
    finally:
        sibs.close()
