# Judging rehearsal

The active database is in the post-correction state because the builder ran the real import and review rehearsal. Re-importing the file creates new review records; it does not reset identities or restore the original demonstration counts. The isolated reproduction command does not reset the active browser database. To rehearse from the original baseline, intentionally run the guarded owner-only reset below before opening role contexts. It creates a backup, verifies the exact local target and synthetic institutions/accounts, replaces the fixed business schema and removes only contained institution storage prefixes. It never runs automatically.

```powershell
python -m app.cli reset --target shiksham --confirm RESET-SYNTHETIC-DEMO --students 100000
```

Keep the backup under ignored `storage/backups`. Never use a remote database for this command. Reset refusal tests pass; runtime reset execution is recorded separately in the audit evidence.

Start the API and web using README, open http://localhost:3000/login, and run `scripts/demo.ps1 show-demo-password` locally. Use separate browser profiles/contexts for each role.

1. Operator A: inspect Institution ledger. In the current post-correction state it has10000total,9881clean,109flagged,10incomplete,119pending,0pending corrections and90.91%submitted. The initial baseline was9000rows; the1,000-row import report retains880/110/10 and140findings. Open Imports and the saved report, then download the error CSV.
2. For a fresh isolated API rehearsal, activate the venv, set PYTHONPATH and run `python scripts/reproduce.py`. It creates a fixed-name scratch database, loads100k, imports the fixture and executes request/correct/approve. This does not provide a clean active browser rehearsal.
3. Student search: type Riya Sharma. The reserved unique name returns one record. Clear/retype to see a cache hit; use the actual API time shown. Representative20-query timings are in benchmark-results.json, not guaranteed example timings.
4. The correction source is row32, enrollment `DEMO-A-0032`; the correct ID is in `fixtures/manifest.json` `correct_to`. Officer requests an identifier correction with a reason; Operator pastes the manifest value with a reason; Officer approves after findings/candidates clear. This action already occurred in the active database, so inspect its saved case and timeline rather than pretending it is still pending. The stale-version API guard returns409.
5. Open the student's timeline and verify its full institution chain. For the isolated tamper demo run `python -m app.cli audit-sandbox create --institution-key institution_a`, inspect its valid output, then run `python -m app.cli audit-sandbox tamper --institution-key institution_a`. The copied chain fails with ROW_HASH_MISMATCH; the production chain remains valid. HTTP sandbox verification is not implemented; explain the explicit CLI boundary.
6. Admin: Institution oversight shows live aggregates; Cases lists masked values. Non-escalated raw student access is forbidden. The core masked view was browser tested; the escalation inspection path needs further regression coverage after its added grant UI.
7. Student: sign in as `student.riya@example.test`. My Passport shows Riya Sharma, the synthetic ID, B.Tech CSE, eight terms, CGPA8.42 and Trust91. Another student's UUID or identifier cannot override SELF scope. Print preview produces three A4 pages; inspect the evidence and formula for clipping.
8. Certificates: choose Trial. Upload `fixtures/certificates/showcase-genuine.pdf`. Local report computes95.00, PDF_TEXT and RULE_BASED with verified-local status. Upload `showcase-tampered.pdf` in another trial. It computes risk83 from NAME_MISMATCH65, PDF_EDIT_METADATA10 and PDF_EDITOR_TOOL8. These are consistency signals, not official authenticity decisions. Trials do not attach to accepted evidence or change trust.
9. Career Copilot: send “Can I become a Data Scientist?” Readiness74 is the sum18+16+14+14+12 from real linked project evidence. Machine Learning16 and Model Deployment10 remain missing. No model or network call is necessary.
10. Trust breakdown: completeness25, local25, certificates16, fraud15, approval10, external0. Explain that mock checks contribute zero official points and that the synthetic fixtures were deliberately chosen to produce the requested demonstration values.
11. Architecture: inspect Search/Import flows and relationship summaries. The current diagrams and table views are smaller than the full requested interaction specification; do not claim all optional controls are complete.

Recovery: retry a failed import only from its saved job checkpoint, using a reason. Missing storage files require re-upload. A missing OCR engine returns UNREADABLE for images. A model failure falls back to rules. Show the actual error and request identifier when a check fails.
