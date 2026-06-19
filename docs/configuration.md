# Configuration

## Constructor

```python
SIBSClient(
    api_key,            # required
    terminal_id,        # required
    environment="sandbox",   # "sandbox" | "production"
    *,
    base_url=None,      # override the resolved base URL (mocks/proxies)
    timeout=30.0,       # seconds
    client_id=None,     # optional X-IBM-Client-Id header value
    webhook_secret=None,
    idempotency_header=None,  # see docs/payments.md
)
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
