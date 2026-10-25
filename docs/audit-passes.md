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

## Automation attempt 4 and focused refactor review

Start **2026-10-25T19:45:44.123645Z**; end **2026-10-25T19:48:45.245500Z**. [Archive](audits/20261025T194544111273Z/automation.json). 12/13 checks passed; only exact artifacts failed. Python: **63 passed**; browser: **7 passed**. Fresh100k seed:77.639s,457482767bytes; showcase acceptance matched. Missing exact paths fell to107 after substantive module extraction.

The entry point now registers twelve domain routers. Auth, institutions, career and trust have schemas/service/repository boundaries. Record matching/rules, import mapping, certificate extract/OCR/risk, audit canonicalization, UTC clock and allowlisted request telemetry are separate implementations with compatibility imports for existing callers. Other routers still contain SQL and business policy; V2 is open.

Independent reviewer /root/independent_review confirmed imports in tested orders, no duplicate method/path operations, schema validation of12institutions/62programs, preservation of career result keys and trust91. Its five findings were treated as defects:

| ID | Severity | Finding | Fix and proof |
|---|---|---|---|
| F1 | Medium | Refactor mistakenly denied student program access required by operation9. | Restore own-institution student access, hide other institutions with404; role regression test covers both. This corrects the builder's earlier interpretation, not a previously existing permission leak. |
| F2 | Medium | Career history omitted top-level readiness_percent required by operation46. | Extract numeric score in repository; include typed field; creation/replay/history integration regression checks74 and one saved session. |
| F3 | Medium | Career plan combined stages into one6week step. | Separate study/project/deployment templates lasting2/3/1weeks per missing skill; unit/API tests assert durations and priorities. |
| F4 | Low | Unknown institution state returned empty200 rather than422. | Validate against states represented in synthetic catalogue; regression checks UNKNOWN_STATE. |
| F5 | Low | Architecture document still placed domain routes in main.py. | Update source map and disclose remaining router-to-service extraction. |

A test-isolation failure during development hit the real login limiter because several new tests reused a shared account. Fixed tests to create isolated synthetic accounts, deactivate them afterward, and preserve the product limiter. No production rate limit was relaxed.

## Automation attempt 5

Start **2026-10-25T19:54:09.885569Z**; end **2026-10-25T19:58:09.174051Z**. [Archive](audits/20261025T195409884571Z/automation.json). Python collection and exact artifacts failed; the other11checks passed. Collection defect T1 (medium test infrastructure): unit and integration modules both named test_career collided under pytest's default import mode. Fixed configuration to importlib mode so domain test filenames coexist. Immediate full Python rerun: **65 passed**. The following full sweep rechecks the fix.

Shared table, badge, loading/error, heading, formatting, typed view aliases and data hook are now extracted from workspace.tsx. The table has an accessible32/44px density toggle. Browser regression verifies pressed state and actual row-height reduction, then restores the default. Print hides controls and resets table spacing; generated A4 passport has3pages. Last page rendered and visually reviewed without clipping. Exact artifact gap is now102paths, with no fixture hash failures. Full screen-state/chart/router-layout work remains V7; these are not complete audit cycles.

## Automation attempt 6

Start **2026-10-25T19:58:53.284725+00:00**; end **2026-10-25T20:01:43.432173+00:00**. [Full archive](audits/20261025T195853284725Z/automation.json). **12/13 checks passed**, process exit1: only exact artifacts remain FAIL (**102 missing paths**, zero fixture hash mismatches, font licenses present). **65 Python tests** and **7 browser flows** passed; production build, client diff, schema/body/grants, scanner, fresh100k and benchmark passed. The collection fix is now verified by the complete sweep. Core acceptance numbers still match.

These are six automation attempts, not six full ordered A?E cycles. The prompt stopping rule remains unsatisfied; V9 stays OPEN. Typed success models now cover12of61operations. Remaining module/repository, typed-contract, UI, OCR and full-conformance work is recorded without claiming completion.
