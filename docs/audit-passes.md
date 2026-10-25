# Audit evidence and remaining gates

The stopping rule is **not satisfied**. These records are automation attempts and independent review rounds, not completed A–E cycles. Clean-checkout reproduction with regenerated secrets, complete individual conformance proof and all specified screens/modules remain outstanding. V9 stays OPEN; no incomplete cycle is counted as clean.

## Automation attempt 1

Retained evidence: [automation summary](audits/attempt-01/automation-summary.txt). Schema, fresh DB, Python lint/types/tests, web lint/types/build, generated client, browser flows and benchmark passed. Placeholder scanning and exact artifacts failed. This older summary lacks per-command timestamps and cannot establish a complete cycle.

A1 (medium): scanner matches in generated requirement prose. Fixed by describing policy markers without embedding prohibited tokens and maintaining the external-variable register. A2 (high conformance gap): missing exact-tree files. Still OPEN as V2; substantive extraction is required. No empty substitute files created.

## Independent review rounds 1 and 2

Reviewer `/root/independent_review` read the specification and source, then rechecked fixes. Round 2 sampled 40 requirements across auth, scope, algorithms, persistence and delivery, plus section 18. Source inspection and in-memory probes do not establish a full runtime cycle.

| Defect | Severity | Fix and proof / remaining limit |
|---|---|---|
| E1 | High | Forbidden runtime audit UPDATE replaced by fixed-search-path security-definer lock. Privilege denial and 100 concurrent append tests pass. |
| E2–E4 | High/medium | Fixed evidence deduplication, explicit name extraction and nested PDF action inspection. Certificate/malicious-PDF regressions pass. |
| E5 | High | Verification locking plus version/idempotency rechecks implemented. Full multi-worker replay remains V4. |
| E6 | Medium | Full API semantics/typing incomplete: V2/V4 OPEN. |
| E7 | High | Concurrent refresh coalesced; browser expiry test passes with one refresh. |
| E8 | Medium | YAML risk thresholds now used by evaluation/trust; tests pass. |
| E9/E12 | High | Missing/invalid admission year handled as findings; regressions pass. |
| E10/E19 | Medium | Fixed program oversight denominator/total/trend and state quality trend; integration regressions pass. |
| E11 | High | Refresh live enrollment claims under advisory lock. Fault rehearsal: two shells, one canonical owner, one conflict. |
| E13 | Medium | Fixed native Excel date parsing; regression passes. |
| E14 | Medium | Added five-per-minute Gemini user limiter; live provider unverified. |
| E15 | Medium | Six supporting image/PDF heuristics remain unassessed: V6 OPEN. |
| E16 | Medium | Schema comparison includes function bodies/runtime grants; independent comparison passes. |
| E17 | Medium | Default sweep now includes fresh 100k scratch reproduction. |
| E18 | High | Audit evidence now recorded; full ordered cycles/stopping rule remain V9 OPEN. |

## Independent review round 3

Reviewer `/root/audit_review_three` sampled 40 checks plus section 18 using source and a pure psycopg connection-parser probe. No concrete sandbox-broker defect found.

| ID | Severity | Evidence, fix and proof |
|---|---|---|
| R3-1 | High | Reset checked parsed hostname while psycopg honored query target overrides. Reject query/fragment and service/host-address/session-option environment overrides; validate effective conninfo and qualify guard tables. Reset regressions pass. No unapproved reset executed. |
| R3-2 | Medium | Benchmark used seeded all-institution officer. Now uses requesting identity/scoped totals; restricted-officer test verifies its assignment only. |
| R3-3 | Medium | Polling had weaker gates/no ownership check. Match POST gates and requested_by restriction; other-officer and controls-off reads return 404 in regression. |
| R3-4 | Medium | Storage manifest absent. Bootstrap now persists it; fresh reproduction produced storage/repro/manifest.json. |
| R3-5 | Low | API docs called delivered HTTP controls unsupported. docs/api.md now distinguishes benchmark/read-only verification from owner-only mutations. |

## Automation attempt 2

Start **2026-10-25T19:21:02.179940Z**; end **2026-10-25T19:25:06.534219Z**.

Command: `.venv/Scripts/python.exe scripts/verify_all.py`. [Raw outputs](audits/attempt-02-20261025T192102/verification-results.json).

**12/13 checks passed**, exit 1. Exact artifacts FAIL: **151 specified paths missing**, **0 fixture hash mismatches**, font licenses present. This is an implementation gap, not an environmental block.

- Scanner, schema/body/grants, lint, mypy, web lint/types/build and generated client PASS.
- **40 Python tests passed**; one dependency deprecation warning.
- **7 browser flows passed**, including mobile/axe, A4 print and concurrent refresh.
- Fresh 100k bootstrap **77.820 seconds**, DB **457,433,615 bytes**; validates identifiers, CGPAs, enrichment ownership and certificate files/hashes.
- Fresh demo: **880/110/10**, **140 findings**, correction **9881/109/10/119**, CGPA **8.42**, trust **91**, readiness **74**, confidence **95**, tampered risk **83**, valid production chain.
- Real benchmark cache-equivalence assertions passed; query samples archived.

After this attempt, nearby security tests including controls-off polling and environment options were rerun: **22 passed**. Next sweep must include the final changes. Future sweeps automatically archive evidence under docs/audits.

## Outstanding work

V2: missing module/component layout/full contracts. V4: remaining API replay/response semantics. V5: individual seed proof and detailed phase timings. V6: visual heuristics/Paddle. V7: all screen states/charts/manual interactions. V9: complete individual conformance, clean-checkout secret regeneration/reproduction and ordered A–E cycles. Docker, hosted CI, cloud, real OCR and live Gemini remain unverified in their owner rows.

## Automation attempt 3

Start 2026-10-25T19:27:36.060828+00:00; end 2026-10-25T19:30:29.032011+00:00. Full evidence: [archived automation](audits/20261025T192736060828Z/automation.json). Again 12/13 checks passed; only the exact-tree gate fails (151 missing paths, zero fixture hash mismatches). 45 Python tests and seven browser flows passed. Fresh 100k bootstrap: 78.665 seconds, 457,466,383 DB bytes; core acceptance outputs matched. This is still not a complete A?E cycle.

R3-6 (high, cloud guard follow-up): parse_qs discarded blank host/SSL query values although psycopg honored them. Fixed with keep_blank_values=True, effective host equality and exact singleton SSL validation. Added pre-connection blank-host/duplicate-SSL regressions; 17 connection-guard tests pass. No remote connection attempted. Final Python-only regression evidence is recorded separately in final-python-regression.json.

Final nearby regression: lint PASS, mypy PASS, **47 Python tests passed** (one dependency deprecation warning). See [raw results](final-python-regression.json). The seven browser flows/build passed in attempt 3 before the final lifecycle-only parser fix; no web code changed afterward.
