"""Materialize the supplied SQL contract without retyping it."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = (ROOT.parent / "shiksham-apaar-build-prompt-v2.md").read_text(encoding="utf-8-sig")
blocks = re.findall(r"~~~sql\n(.*?)~~~", spec, re.DOTALL)
schema, audit, views, supplements = [], [], [], []
for block in blocks:
    if block.startswith("UPDATE demo_sandbox"):
        continue
    if "CREATE MATERIALIZED VIEW" in block or "CREATE FUNCTION refresh_demo_views" in block:
        views.append(block)
    elif "CREATE TABLE audit_chains" in block:
        audit.append(block)
    elif (
        block.startswith("CREATE TABLE api_idempotency")
        or block.startswith("CREATE TABLE program_expected_records")
        or block.startswith("ALTER TABLE certificates")
    ):
        supplements.append(block)
    elif (
        block.startswith("CREATE EXTENSION")
        or block.startswith("CREATE FUNCTION check_term_integrity")
        or block.startswith("CREATE INDEX ix_students_quality")
    ):
        schema.append(block)
for directory in [
    "db/seed",
    "apps/api/app/core",
    "apps/api/app/db",
    "apps/api/app/config",
    "apps/api/app/integrations",
    "apps/api/alembic/versions",
    "apps/api/tests/unit",
    "apps/api/tests/integration",
    "apps/api/tests/performance",
    "apps/web/public/fonts",
    "packages/api-client",
    "fixtures/certificates",
    "storage",
    ".github/workflows",
]:
    (ROOT / directory).mkdir(parents=True, exist_ok=True)
for path, content in [
    ("db/core.sql", "\n".join(schema + supplements)),
    ("db/audit.sql", "\n".join(audit)),
    ("db/views.sql", "\n".join(views)),
]:
    (ROOT / path).write_text(content, encoding="utf-8")
(ROOT / "db/schema.sql").write_text("\n".join(schema + supplements + audit + views), encoding="utf-8")
for path in ["db/__init__.py", "db/seed/__init__.py", "apps/api/app/__init__.py", "storage/.gitkeep"]:
    (ROOT / path).touch()
