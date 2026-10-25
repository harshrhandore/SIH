"""Bounded readiness wait for CI; never invent a service-ready result."""

import time
import urllib.request

for attempt in range(45):
    try:
        with urllib.request.urlopen("http://localhost:3000/login", timeout=2) as r:
            if r.status == 200:
                print("Web ready.")
                break
    except Exception:
        pass
    time.sleep(1)
else:
    raise SystemExit("Web did not become ready within 45 attempts.")
