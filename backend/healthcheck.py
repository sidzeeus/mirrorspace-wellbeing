"""Container health probe:  python healthcheck.py [path]

Uses only the standard library. The Host header is taken from DJANGO_ALLOWED_HOSTS so
the probe passes Django's host validation in every environment.
"""

import os
import sys
import urllib.request

path = sys.argv[1] if len(sys.argv) > 1 else "/api/v1/health"
host = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")[0].strip() or "localhost"
request = urllib.request.Request(f"http://127.0.0.1:8000{path}", headers={"Host": host})  # noqa: S310
try:
    with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310
        sys.exit(0 if response.status == 200 else 1)
except Exception:  # noqa: BLE001
    sys.exit(1)
