"""Compare disposable tables with genuine planner choices; never alter live indexes."""

import json
from pathlib import Path
from dotenv import dotenv_values
import psycopg
from check_schema import database_url

ROOT = Path(__file__).resolve().parents[1]
url = database_url(dotenv_values(ROOT / ".env")["DATABASE_OWNER_URL"], "shiksham_bench_100000")
with psycopg.connect(url) as conn:
    for table in ["explain_baseline", "explain_indexed"]:
        conn.execute("DROP TABLE IF EXISTS " + table)
        conn.execute("CREATE TABLE " + table + " AS SELECT id,institution_id,normalized_name FROM students")
        conn.execute("ALTER TABLE " + table + " ADD PRIMARY KEY(id)")
    conn.execute("CREATE INDEX explain_name_gin ON explain_indexed USING gin(normalized_name gin_trgm_ops)")
    conn.execute("CREATE INDEX explain_scope ON explain_indexed(institution_id)")
    conn.execute("ANALYZE explain_baseline")
    conn.execute("ANALYZE explain_indexed")
    plans = {}
    for table in ["explain_baseline", "explain_indexed"]:
        plans[table] = conn.execute(
            "EXPLAIN(ANALYZE,BUFFERS,FORMAT JSON) SELECT id FROM " + table + " WHERE normalized_name LIKE %s",
            ("%riya sharma%",),
        ).fetchone()[0]
    (ROOT / "docs/explain-results.json").write_text(json.dumps(plans, indent=2))
    conn.execute("DROP TABLE explain_baseline,explain_indexed")
print("Recorded actual baseline/indexed plans from disposable benchmark tables.")
