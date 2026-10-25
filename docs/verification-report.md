# Verification report

This is a partial implementation and measured local verification report, not completion of the full prompt. Native Windows/PostgreSQL16 is the execution path. The exact audit stopping rule and full specification remain incomplete (V9). Docker is UNVERIFIED-ENV (V1); cloud preview is UNVERIFIED-HUMAN (V3); live Gemini/PNG OCR are UNVERIFIED-ENV (V10); hosted CI is UNVERIFIED-HUMAN (V11).

## Vertical slices

| Phase | Measured behavior | Remaining gates |
|---|---|---|
| 1 | 100k bootstrap, four roles, scoped search, refresh reuse, fresh DB, schema | Exact module tree V2; Docker V1 |
| 2 | 880/110/10,140findings,50pairs,120cases; crash500→501; correction counts9881/109/10/119 | Broader import/API adversarial coverage V4,V9 |
| 3 | 100concurrent appends, runtime privilege tests, valid production chain and broken sandbox, masking | Full grants and analytics/UI contract V4,V7,V9 |
| 4 | CGPA8.42, PDF confidence95, tampered risk83, trust91, readiness74;3page print; browser flows | Visual fraud/Paddle V6; real OCR/model V10 |
| 5 | Local lint/type/build/client, seven browser flows, isolated50k/100k benchmark, EXPLAIN, synthetic fraud sanity | Exact artifacts V2; broad screen/seed/audit/CI V5,V7,V9,V11 |

## Latest automation sweep

| Check | Result | Started UTC | Command |
|---|---|---|---|
| placeholders/secrets | PASS | 2026-10-25T19:27:36.060828+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_placeholders.py |
| schema | PASS | 2026-10-25T19:27:36.643839+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_schema.py |
| fresh database | PASS | 2026-10-25T19:27:39.747968+00:00 | [repo]\.venv\Scripts\python.exe scripts/reproduce.py |
| python lint | PASS | 2026-10-25T19:29:16.389373+00:00 | [repo]\.venv\Scripts\python.exe -m ruff check --config apps/api/pyproject.toml apps/api/app |
| python types | PASS | 2026-10-25T19:29:16.630977+00:00 | [repo]\.venv\Scripts\python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app |
| python tests | PASS | 2026-10-25T19:29:19.419277+00:00 | [repo]\.venv\Scripts\python.exe -m pytest apps/api/tests -q |
| web lint | PASS | 2026-10-25T19:29:35.887810+00:00 | npm.cmd run lint |
| web types | PASS | 2026-10-25T19:29:47.349823+00:00 | npm.cmd run typecheck |
| web build | PASS | 2026-10-25T19:29:52.064369+00:00 | npm.cmd run build |
| generated client | PASS | 2026-10-25T19:30:03.626659+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_client.py |
| browser flows | PASS | 2026-10-25T19:30:08.582297+00:00 | npm.cmd run e2e |
| artifacts | FAIL | 2026-10-25T19:30:24.484915+00:00 | [repo]\.venv\Scripts\python.exe scripts/check_artifacts.py |
| benchmark | PASS | 2026-10-25T19:30:24.665782+00:00 | [repo]\.venv\Scripts\python.exe scripts/benchmark.py --runs 20 |

Raw commands, outputs, exit codes and timestamps are in verification-results.json. Additional measured evidence: acceptance-results.json, reproduction-results.json, fault-rehearsal-results.json, audit-sandbox-clean.json, audit-sandbox-tampered.json, volume-benchmark-results.json, explain-results.json, fraud-benchmark.json, schema-check.json and playwright-results.json.

Final lifecycle regression: 47 Python tests, lint and mypy pass (final-python-regression.json). Seven browser flows cover role screens, mobile/axe, print and concurrent refresh. The latest fresh seed also independently validates all canonical identifiers, cumulative credit-weighted grades, enrichment ownership percentages, certificate bytes and file hashes. Web benchmark requests use the requesting officer's institution assignments; polling is owner-scoped and respects the same local demo gates. These targeted checks do not close the broader V4/V5/V7/V9 requirements.

The exact-tree checker reports missing files rather than generating hollow substitutes. The owner register records incomplete implementation, decisions, provider placeholders and every human-only item. No cloud service was provisioned and no remote was added or pushed.
