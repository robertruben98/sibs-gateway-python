# Errors

All exceptions inherit from `SIBSError`, so you can catch everything with one class or
handle specific cases.

| Exception | Raised when |
| --- | --- |
| `SIBSConfigurationError` | Misconfiguration (missing credentials, bad environment, bad timeout). |
| `SIBSValidationError` | Local input validation fails (float amount, empty id, bad URL). |
| `SIBSAuthenticationError` | SIBS rejects credentials (HTTP 401/403). |
| `SIBSAPIError` | Other API errors; carries `status_code` and `response_body`. |
| `SIBSTimeoutError` | Request times out, or HTTP 408. |
| `SIBSConnectionError` | SIBS unreachable (DNS/TCP/TLS). |
| `SIBSInvalidWebhookSignature` | Webhook signature verification fails (with `raise_on_failure=True`). |

```python
from pysibs import SIBSError, SIBSAPIError, SIBSAuthenticationError

try:
    client.create_payment(amount="10.00", merchant_transaction_id="ORDER-1")
except SIBSAuthenticationError:
    ...  # refresh/inspect credentials
except SIBSAPIError as exc:
    print(exc.status_code, exc.response_body)
except SIBSError:
    ...  # any other PySIBS failure
```

Raw `httpx` exceptions are always translated into one of the above; they never leak to
the caller. Exception messages and bodies never contain the request payload or
credentials.
