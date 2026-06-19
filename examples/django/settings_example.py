"""Illustrative settings snippet for the Django example.

Read credentials from the environment (e.g. via django-environ or os.environ); never
hard-code them. The PySIBS client itself does not read Django settings -- it is
constructed in ``views.py`` via ``SIBSClient.from_env()``.
"""

from __future__ import annotations

import os

# Used by the webhook view to verify signatures.
SIBS_WEBHOOK_SECRET = os.environ.get("SIBS_WEBHOOK_SECRET", "")

# The following SIBS_* environment variables are consumed by SIBSClient.from_env():
#   SIBS_API_KEY, SIBS_TERMINAL_ID, SIBS_ENVIRONMENT, SIBS_CLIENT_ID (optional)
