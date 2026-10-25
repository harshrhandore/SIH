# Deterministic algorithms

Synthetic identifiers are `SYN-` plus twelve base digits and one Luhn digit. They are not real APAAR identifiers. Names use NFC, Unicode case folding, title removal and punctuation/whitespace normalization; Unidecode aids matching. Token-set similarity requires a token-count and token-sort guard before a high-confidence match.

Import rule precedence is missing mandatory, missing ID, invalid ID, duplicate ID, name inconsistency, enrollment conflict, impossible academic values, possible duplicate. A row has one primary finding; secondary findings remain queryable. The supplied fixture computes 120 primary and 20 secondary findings, 50 candidate pairs and 120 review cases. Identity candidates never merge students.

Possible-duplicate score is 75% name + 20% exact DOB + 5% parent similarity, with name at least 90, score at least 87 and corroborating DOB or parent information. Current matching primarily uses exact-DOB blocks; the parent-only candidate-discovery branch remains a gap.

Certificate confidence is 100 × (0.50 name + 0.20 issuer + 0.15 date + 0.15 credential syntax), rounded half-up. The generic credential fraction is computed with Decimal 2/3. The genuine fixture intentionally yields 95.00; it is local document consistency, not issuer authentication. Risk weights are loaded from the versioned YAML catalogue. Name mismatch contributes 65, an edited metadata interval contributes 10 and an editor-tool indicator contributes 8 for the tampered fixture's measured 83. Image heuristics and pHash are explicitly listed as not assessed in this implementation.

Trust components are completeness 25, local findings 25, accepted certificates 20, fraud hygiene 15, current-version approval 10 and official external verification 5. Official points are always zero. Two distinct accepted local certificates contribute 16, yielding 25+25+16+15+10=91. Evidence deduplicates by either SHA or issuer/credential. Trials never enter the accepted evidence or risk calculation; unreviewed high-risk passport submissions do.

Career readiness sums the weights of scoped evidenced skills with proficiency at least two. Data Scientist weights are Python18, SQL16, Statistics14, Pandas14, Data Visualization12, Machine Learning16 and Model Deployment10. The first five total 74. No model response changes this score.

Audit values exclude floats. NFC canonical JSON is sorted, compact and Unicode-preserving. Each row hashes the preceding 64-character lowercase hash concatenated with the exact canonical event text. The verifier checks the full snapshot's sequence, relational envelope, canonicalization, hashes and stored head. `lock_audit_chain` is a fixed-search-path definer helper needed because PostgreSQL row locks require privileges the runtime must not receive directly.
