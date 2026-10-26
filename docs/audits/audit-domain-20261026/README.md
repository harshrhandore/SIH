# Audit domain checkpoint

Recorded 2026-10-26T03:01:10.391455+00:00. This is a focused implementation and review checkpoint, not a complete ordered audit cycle or full conformance claim.

Audit routes now delegate SQL to a repository and authorization/chain verification to a service. Typed models cover timeline, chain summary and masked event summaries. Owner sandbox management is separate from the runtime read broker. Compatibility imports preserve existing append callers. OpenAPI documents bearer authorization and has 15/61 typed JSON success contracts.

Timeline authorization, grant validation, full chain verification and event pagination share one repeatable-read, read-only snapshot. Qualified event columns fix the joined student_id ambiguity. Admin summaries omit reason/actor/payload without a valid scoped grant; broad raw-grant requests are rejected. Grants bind to the requested case, actual student, actor and current case version. Foreign case filters return404 before filter mismatch details. HMAC case references omit raw identifiers.

Independent source review found missing null-safe system-chain lookup and same-student/different-case grant binding. Both were fixed and regression-tested. Seed creates a distinct system chain; bootstrap verifies it. The existing local demo received an idempotent owner-only insertion of the missing empty system chain, preserving every production event and head. `python -m app.cli audit-system` is read-only and returned valid=true, head_seq=0. No HTTP system-chain query was added. Review follow-up was unavailable due model capacity; no re-review completion is claimed.

Verification:

- Full Python suite:72 passed, one upstream Starlette/httpx deprecation warning.
- Ruff backend lint:PASS; configured mypy:PASS across74source files.
- Migrated schema, constraints, indexes, function bodies and runtime grants:PASS.
- Generated OpenAPI/client:PASS using the activated project virtual environment.
- Placeholder/secret and UI encoding scan:PASS.
- Fresh isolated100k bootstrap:59.680seconds,457482767database bytes; acceptance import880/110/10,140findings, post-correction9881/109/10, trust91/readiness74/PDF95/tampered83/validchain. Raw output archived beside this file.
- New real-browser `audit-demo.spec.ts`:1passed, verifying assigned-officer timeline, real chain result, stored row hashes,25/50selection and re-verification.
- The broader UI suite was interrupted after failures while UI controls were changing in another active working session. A targeted student flow passed its new timeline assertions but later failed waiting for saved career history. This checkpoint does not claim a new full browser pass.
- Exact-tree gate remains FAIL:42missing paths and zero fixture hash mismatches at this checkpoint. Required unit test files now contain the existing algorithm/document assertions split by domain; they are not hollow substitutes.

Remaining: full API contract typing, remaining service/repository boundaries, combined passport network-failure isolation, broader UI/adversarial coverage, visual OCR/fraud providers, environment-dependent Docker/cloud/CI and complete ordered audit cycles. Existing owner rows remain open.
