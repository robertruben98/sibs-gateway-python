# Django integration

PySIBS has no Django dependency; you just use the client inside your views.

See the runnable example under [`examples/django/`](../examples/django/):

- [`views.py`](../examples/django/views.py) — create payment, check status, webhook.
- [`urls.py`](../examples/django/urls.py) — URL wiring.
- [`settings_example.py`](../examples/django/settings_example.py) — settings snippet.

## Notes

- Construct the client once (module level) and reuse it; it is safe to share.
- The webhook view must be `@csrf_exempt` (SIBS won't send a CSRF token) and should
  verify the signature before trusting the payload.
- Respond `200` quickly from the webhook so SIBS does not retry unnecessarily.

```python
from pysibs import SIBSClient

client = SIBSClient.from_env()  # reads SIBS_* env vars
```
