import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps/api"), str(ROOT)]
from app.main import app

(ROOT / "packages/api-client/openapi.json").write_text(
    json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8", newline="\n"
)
print("Exported FastAPI OpenAPI schema.")
