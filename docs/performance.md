# Measured performance

Measurements are synthetic local demonstrations, not a production SLA. API timers exclude network; TestClient roundtrips are in-process. Twenty fixed query samples use warm database buffers. p95 is the nearest-rank sample at ceil(.95*n)-1.

| Dataset | Seed total seconds | Database bytes | Application-cold p50/p95 ms | Cached p50/p95 ms |
|---|---:|---:|---:|---:|
| 50000 | 30.982 | 240443919 | 9.3515/40.763 | 2.7375/3.216 |
| 100000 | 57.463 | 457507343 | 12.6465/84.803 | 2.8745000000000003/3.196 |

Hardware: Windows11,16logical CPUs,16,625,724KiB RAM, AMD64 Family25 Model80 Stepping0; local portable PostgreSQL16.15, shared_buffers256MB,max_connections40. Physical storage model and judging-laptop identity remain owner checks. See the raw benchmark JSON for every query and roundtrip sample.

`docs/explain-results.json` contains real EXPLAIN ANALYZE/BUFFERS JSON comparing disposable tables with primary keys only against equivalent data with the requested search indexes. No live index was dropped and no planner option was disabled.

Synthetic fraud sanity check: {"true_positive": 30, "false_positive": 0, "true_negative": 30, "false_negative": 0}. These60controlled documents do not measure real-world accuracy.

The owner must run `python scripts/benchmark.py --runs 20` on the actual judging laptop and add its output here.
