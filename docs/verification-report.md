# Verification report

This is a historical full-sweep checkpoint. Read [current project status](project-status.md) and [the later UI audit](ui-audit/README.md) for the updated source, browser evidence, retired UI requirements and hosted CI finding. The measurements below retain their original scope and timestamps.

This is a partial implementation and measured local verification report, not completion of the full prompt. Native Windows/PostgreSQL16 is the execution path. The exact audit stopping rule and full specification remain incomplete (V9). Docker is UNVERIFIED-ENV (V1); cloud preview is UNVERIFIED-HUMAN (V3); live Gemini/PNG OCR are UNVERIFIED-ENV (V10); hosted CI is UNVERIFIED-HUMAN (V11).

Source checkpoint: `f13cf0ad6b67063cbb49f6ffadcaec20d78d07d1`. Report generated 2026-10-26T02:27:31.396052+00:00. Raw sweep timestamps below identify the tested working state.

## Vertical slices

| Phase | Measured behavior | Remaining gates |
|---|---|---|
| 1 | 100k bootstrap, four roles, scoped search, refresh reuse, fresh DB, schema | Exact module tree V2; Docker V1 |
| 2 | 880/110/10,140findings,50pairs,120cases; crash500→501; correction counts9881/109/10/119 | Broader import/API adversarial coverage V4,V9 |
| 3 | 100concurrent appends, runtime privilege tests, valid production chain and broken sandbox, masking | Full grants and analytics/UI contract V4,V7,V9 |
| 4 | CGPA8.42, PDF confidence95, tampered risk83, trust91, readiness74;3page print; browser flows | Visual fraud/Paddle V6; real OCR/model V10 |
| 5 | Local lint/type/build/client, browser flows, isolated50k/100k benchmark, EXPLAIN, synthetic fraud sanity | Exact artifacts V2; broad screen/seed/audit/CI V5,V7,V9,V11 |

## Latest automation sweep

| Check | Result | Started UTC | Command |
|---|---|---|---|
| placeholders/secrets | PASS | 2026-10-26T02:13:36.675880+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_placeholders.py |
| schema | PASS | 2026-10-26T02:13:37.128670+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_schema.py |
| fresh database | PASS | 2026-10-26T02:13:39.628855+00:00 | [repo]\.venv\Scripts\python.exe scripts/reproduce.py |
| python lint | PASS | 2026-10-26T02:14:44.348502+00:00 | [repo]\.venv\Scripts\python.exe -m ruff check --config apps/api/pyproject.toml apps/api/app |
| python types | PASS | 2026-10-26T02:14:45.022635+00:00 | [repo]\.venv\Scripts\python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app |
| python tests | PASS | 2026-10-26T02:14:46.607421+00:00 | [repo]\.venv\Scripts\python.exe -m pytest apps/api/tests -q |
| web lint | PASS | 2026-10-26T02:15:00.127930+00:00 | npm.cmd run lint |
| web types | PASS | 2026-10-26T02:15:09.453216+00:00 | npm.cmd run typecheck |
| web build | PASS | 2026-10-26T02:15:12.561470+00:00 | npm.cmd run build |
| generated client | PASS | 2026-10-26T02:15:21.821977+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_client.py |
| browser flows | PASS | 2026-10-26T02:15:25.628384+00:00 | npm.cmd run e2e |
| artifacts | FAIL | 2026-10-26T02:15:48.823852+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_artifacts.py |
| benchmark | PASS | 2026-10-26T02:15:48.940127+00:00 | [repo]\.venv\Scripts\python.exe scripts/benchmark.py --runs 20 |

Raw commands, outputs, exit codes and timestamps are in verification-results.json. Additional measured evidence: acceptance-results.json, reproduction-results.json, fault-rehearsal-results.json, audit-sandbox-clean.json, audit-sandbox-tampered.json, volume-benchmark-results.json, explain-results.json, fraud-benchmark.json, schema-check.json and playwright-results.json.

Latest Python suite: PASS; 65 tests passed; raw results above are authoritative. Historical lifecycle-only evidence remains in final-python-regression.json. 14 browser checks passed and 0 failed in the latest browser result. Coverage includes role screens, keyboard palette/drawer, scoped filters/charts, loading privacy, print and concurrent refresh. The latest fresh seed also independently validates all canonical identifiers, cumulative credit-weighted grades, enrichment ownership percentages, certificate bytes and file hashes. Web benchmark requests use the requesting officer's institution assignments; polling is owner-scoped and respects the same local demo gates. These targeted checks do not close the broader V4/V5/V7/V9 requirements.

Exact artifact gap: 55 required paths absent; 0 fixture hash mismatches. 12 of 61 current operations have typed JSON success models; the remaining response contracts and repository boundaries stay open.

The exact-tree checker reports missing files rather than generating hollow substitutes. The owner register records incomplete implementation, decisions, provider placeholders and every human-only item. No cloud service was provisioned and no remote was added or pushed.
