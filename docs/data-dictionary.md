# Data dictionary

`institutions`, `programs` and `program_expected_records` define scope and expected submission denominators. `users`, `roles`, `user_institutions` and `refresh_sessions` define capabilities, assignments and rotated sessions.

`students` contains canonical accepted keys and separately preserved submitted keys. A nullable shell retains incomplete imports. `enrolments` and `academic_performance` enforce student/program/term consistency; `performance_subjects` is optional detail. Placements, projects, internships, skills, achievements, scholarships and certificates are normalized child records.

`import_batches`, `import_rows`, `import_errors` and `import_jobs` retain original staging, findings and checkpoints. `verification_findings`, `duplicate_candidates`, `review_cases`, `review_decisions` and `record_versions` retain discrepancy and human-review history. No decision performs identity merging.

`audit_chains` stores chain heads; immutable `audit_events` stores relational envelopes, canonical text and hashes. `certificate_verifications`, `trust_scores`, `career_sessions` and `external_verifications` hold explainable computed outputs. `institution_epochs` invalidates scoped caches; four materialized views and refresh/snapshot tables provide measured analytics.

See executable SQL for every type, check, foreign key, index and trigger. `scripts/check_schema.py` compares the migrated catalogues against independent SQL execution.
