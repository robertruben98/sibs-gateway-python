# Configuration

## Constructor

```python
SIBSClient(
    api_key,            # required
    terminal_id,        # required
    environment="sandbox",   # "sandbox" | "production"
    *,
    base_url=None,      # override the resolved base URL (mocks/proxies)
    timeout=30.0,       # seconds, or an httpx.Timeout for connect/read/write/pool
    retries=None,       # RetryConfig | int | None (None = sensible defaults; 0 disables)
    verify=True,        # TLS verification, or a path to a custom CA bundle
    proxy=None,         # e.g. "http://proxy.local:8080"
    client_id=None,     # optional X-IBM-Client-Id header value
    webhook_secret=None,
    idempotency_header=None,  # see docs/payments.md
)
```

### Retries, timeouts & TLS

```python
from pysibs import RetryConfig
import httpx

client = SIBSClient(
    api_key="...", terminal_id="...",
    retries=RetryConfig(max_retries=3, backoff_factor=0.5, max_backoff=30),
    timeout=httpx.Timeout(connect=2.0, read=10.0, write=10.0, pool=2.0),
)
```

Retries are payment-safe: idempotent methods (`GET`) retry on connection errors,
timeouts and retryable statuses; non-idempotent methods (`POST`) retry **only** on
`429`/`503`. `Retry-After` is honoured. Pass `retries=0` to disable, or `retries=3` as a
shorthand for `RetryConfig(max_retries=3)`.

### Logging

PySIBS logs to the `pysibs` logger at `DEBUG` (method, path, status, elapsed, attempt) —
never headers, bodies or credentials. It attaches no handler; configure logging in your
app:

```python
import logging
logging.getLogger("pysibs").setLevel(logging.DEBUG)
```

## From environment variables

`SIBSClient.from_env()` reads:

| Variable | Required | Meaning |
| --- | --- | --- |
| `SIBS_API_KEY` | yes | Bearer token sent in `Authorization`. |
| `SIBS_TERMINAL_ID` | yes | Terminal id used in the request payload. |
| `SIBS_ENVIRONMENT` | no | `sandbox` (default) or `production`. |
| `SIBS_CLIENT_ID` | no | Value for the `X-IBM-Client-Id` header. |
| `SIBS_WEBHOOK_SECRET` | no | Shared secret for webhook verification. |

The **core library never reads `.env`**. The bundled examples load `.env` via
`python-dotenv`.

## Base URLs

Resolved per environment (see `pysibs/config.py`). Override `base_url` to point at a
mock or proxy. Verify the production/sandbox hosts against the current official SIBS
documentation before going live.
