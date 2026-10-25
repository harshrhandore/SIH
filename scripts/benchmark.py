"""Read-only current-dataset search benchmark; application cache semantics are explicit."""

import argparse
import json
import math
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import issue, hash_token
from app.db.session import connect, one
from app.core.algorithms import synthetic_id


def percentiles(values):
    ordered = sorted(values)
    return dict(
        min_ms=min(values),
        max_ms=max(values),
        p50_ms=statistics.median(values),
        p95_ms=ordered[math.ceil(0.95 * len(values)) - 1],
    )


def benchmark(runs=20, requester_id=None):
    client = TestClient(app)
    with connect() as conn:
        requester = one(conn, "SELECT * FROM users WHERE id=%s AND active", (requester_id,)) if requester_id else None
        if requester_id and (not requester or requester["role_code"] not in {"OFFICER", "ADMIN"}):
            raise RuntimeError("Benchmark requester is no longer authorized.")
        officer = (
            requester
            if requester and requester["role_code"] == "OFFICER"
            else one(conn, "SELECT * FROM users WHERE email='officer@example.test' AND role_code='OFFICER' AND active")
        )
        if not officer:
            raise RuntimeError("Synthetic benchmark officer is unavailable.")
        tokens = issue(conn, officer)
        scope = [
            r["institution_id"]
            for r in conn.execute(
                "SELECT institution_id FROM user_institutions WHERE user_id=%s", (officer["id"],)
            ).fetchall()
        ]
        student_count = one(conn, "SELECT count(*) AS n FROM students WHERE institution_id=ANY(%s::uuid[])", (scope,))[
            "n"
        ]
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    queries = [
        "q=Riya",
        "q=Sharma",
        "q=Riya%20Sharma",
        "q=" + quote("Śhármá"),
        "q=NoSuchSyntheticName",
        "q=SYN-0000000000018",
        "q=" + synthetic_id(999999999999),
        "q=SYN-A-000002",
        "q=SYN-A-000003",
        "branch=CSE",
        "branch=ECE",
        "current_year=4",
        "q=Sharma&branch=CSE",
        "q=Riya&current_year=4",
        "page=1",
        "page=10",
        "branch=IT&current_year=2",
        "q=" + synthetic_id(1001),
        "q=An",
        "current_year=1",
    ]
    cold, hot, roundtrip_cold, roundtrip_hot = [], [], [], []
    samples = []
    client.get("/api/v1/students/search?q=Riya", headers=headers)
    for i in range(runs):
        query = queries[i % len(queries)]
        start = perf_counter()
        a = client.get("/api/v1/students/search?" + query, headers={**headers, "X-Demo-Cache": "bypass"})
        roundtrip_cold.append((perf_counter() - start) * 1000)
        assert a.status_code == 200, a.text
        client.get("/api/v1/students/search?" + query, headers=headers)
        start = perf_counter()
        b = client.get("/api/v1/students/search?" + query, headers=headers)
        roundtrip_hot.append((perf_counter() - start) * 1000)
        assert b.status_code == 200, b.text
        a, b = a.json(), b.json()
        assert a["total"] == b["total"] and a["items"] == b["items"] and b["cache"] == "HIT"
        cold.append(a["took_ms"])
        hot.append(b["took_ms"])
        samples.append(dict(query=query, total=a["total"], cold_ms=a["took_ms"], cached_ms=b["took_ms"]))
    with connect() as conn:
        conn.execute(
            "UPDATE refresh_sessions SET revoked_at=now() WHERE token_hash=%s", (hash_token(tokens["refresh_token"]),)
        )
    return dict(
        student_count=student_count,
        institution_scope=[str(sid) for sid in scope],
        application_cold=percentiles(cold),
        cached=percentiles(hot),
        testclient_roundtrip_cold=percentiles(roundtrip_cold),
        testclient_roundtrip_cached=percentiles(roundtrip_hot),
        samples=samples,
        hardware=platform.platform() + "; " + platform.processor(),
        cache_semantics="Application cold bypasses only result cache; database buffers remain warm. TestClient roundtrip is in-process, not browser network latency.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--volume", default="current", choices=["current"])
    parser.add_argument("--output", default="docs/benchmark-results.json")
    args = parser.parse_args()
    result = benchmark(args.runs)
    (ROOT / args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ["application_cold", "cached", "hardware"]}))
