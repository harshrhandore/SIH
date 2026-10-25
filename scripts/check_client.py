import os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / "packages/api-client/openapi.json", ROOT / "apps/web/src/lib/generated/api.d.ts"]
before = [p.read_bytes() if p.exists() else b"" for p in paths]
r = subprocess.run(["npm.cmd" if os.name == "nt" else "npm", "run", "api:generate"], cwd=ROOT)
if r.returncode:
    raise SystemExit(r.returncode)
if before != [p.read_bytes() for p in paths]:
    print("Generated client was stale; regenerated it. Review and rerun.")
    raise SystemExit(1)
print("Generated OpenAPI and client are current.")
