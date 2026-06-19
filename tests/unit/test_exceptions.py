from __future__ import annotations

from pysibs import SIBSAPIError, SIBSError


def test_api_error_carries_status_and_body() -> None:
    err = SIBSAPIError("boom", status_code=500, response_body={"x": 1})
    assert err.status_code == 500
    assert err.response_body == {"x": 1}
    assert "500" in str(err)
    assert isinstance(err, SIBSError)


def test_api_error_without_status() -> None:
    err = SIBSAPIError("boom")
    assert str(err) == "boom"
    assert err.status_code is None
