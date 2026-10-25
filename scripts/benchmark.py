"""Read-only current-dataset search benchmark; application cache semantics are explicit."""

import argparse
import json
import math
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app


def percentiles(values):
    ordered = sorted(values)
    return dict(
        min_ms=min(values),
        max_ms=max(values),
        p50_ms=statistics.median(values),
        p95_ms=ordered[math.ceil(0.95 * len(values)) - 1],
    )


def benchmark(runs=20):
    client = TestClient(app)
    password = dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]
    tokens = client.post("/api/v1/auth/login", json=dict(email="officer@example.test", password=password)).json()
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    queries = [
        "q=Riya",
        "q=Sharma",
        "q=Riya%20Sharma",
        "q=Aarav",
        "q=NoSuchSyntheticName",
        "q=SYN-0000000000018",
        "q=SYN-9999999999999",
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
        "q=Kumar",
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
    return dict(
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
