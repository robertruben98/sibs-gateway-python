from __future__ import annotations

import pytest

from pysibs import SIBSClient, SIBSConfigurationError, SIBSEnvironment
from pysibs.config import BASE_URLS, ClientConfig


def test_client_initialization_defaults() -> None:
    client = SIBSClient(api_key="k", terminal_id="t")
    assert client.config.environment is SIBSEnvironment.SANDBOX
    assert client.config.base_url == BASE_URLS[SIBSEnvironment.SANDBOX]
    client.close()


def test_client_initialization_production() -> None:
    client = SIBSClient(api_key="k", terminal_id="t", environment="production")
    assert client.config.environment is SIBSEnvironment.PRODUCTION
    assert client.config.base_url == BASE_URLS[SIBSEnvironment.PRODUCTION]
    client.close()


def test_missing_api_key_raises_error() -> None:
    with pytest.raises(SIBSConfigurationError):
        SIBSClient(api_key="", terminal_id="t")


def test_missing_terminal_id_raises_error() -> None:
    with pytest.raises(SIBSConfigurationError):
        SIBSClient(api_key="k", terminal_id="  ")


def test_invalid_environment_raises_error() -> None:
    with pytest.raises(SIBSConfigurationError):
        SIBSClient(api_key="k", terminal_id="t", environment="staging")


def test_invalid_timeout_raises_error() -> None:
    with pytest.raises(SIBSConfigurationError):
        SIBSClient(api_key="k", terminal_id="t", timeout=0)


def test_environment_coerce_accepts_enum() -> None:
    assert SIBSEnvironment.coerce(SIBSEnvironment.PRODUCTION) is SIBSEnvironment.PRODUCTION
    assert SIBSEnvironment.coerce("SANDBOX") is SIBSEnvironment.SANDBOX


def test_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIBS_API_KEY", "env_key")
    monkeypatch.setenv("SIBS_TERMINAL_ID", "999")
    monkeypatch.setenv("SIBS_ENVIRONMENT", "production")
    monkeypatch.setenv("SIBS_CLIENT_ID", "cid")
    client = SIBSClient.from_env()
    assert client.config.api_key == "env_key"
    assert client.config.terminal_id == "999"
    assert client.config.environment is SIBSEnvironment.PRODUCTION
    assert client.config.client_id == "cid"
    client.close()


def test_from_env_missing_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIBS_API_KEY", raising=False)
    monkeypatch.setenv("SIBS_TERMINAL_ID", "999")
    with pytest.raises(SIBSConfigurationError):
        ClientConfig.from_env()


def test_base_url_override_strips_trailing_slash() -> None:
    client = SIBSClient(api_key="k", terminal_id="t", base_url="https://x.test/api/")
    assert client.config.base_url == "https://x.test/api"
    client.close()
