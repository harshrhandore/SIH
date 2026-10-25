# Relational model

The executable contract is `db/schema.sql`; migrations execute its three constituent SQL files in order. Constraints prevent invalid canonical identifiers and enforce institution/program consistency. Incomplete submitted values stay in staging and nullable shell fields.

```mermaid
erDiagram
 institutions ||--o{ programs : offers
 institutions ||--o{ students : scopes
 institutions ||--o{ import_batches : receives
 institutions ||--|| audit_chains : records
 programs ||--o{ students : enrolls
 programs ||--|| program_expected_records : expects
 students ||--o{ enrolments : has
 enrolments ||--|| academic_performance : measures
 academic_performance ||--o{ performance_subjects : details
 students ||--o{ placements : receives
 students ||--o{ certificates : presents
 certificates ||--o{ certificate_verifications : checks
 students ||--o{ projects : builds
 students ||--o{ internships : attends
 students ||--o{ student_skills : evidences
 skills ||--o{ student_skills : defines
 students ||--o{ achievements : earns
 students ||--o{ scholarships : receives
 students ||--o{ verification_findings : flags
 students ||--o{ review_cases : reviews
 review_cases ||--o{ review_decisions : records
 students ||--o{ record_versions : preserves
 students ||--o| trust_scores : computes
 students ||--o{ career_sessions : asks
 students ||--o{ duplicate_candidates : candidate_a
 students ||--o{ duplicate_candidates : candidate_b
 users ||--o{ refresh_sessions : rotates
 users ||--o{ user_institutions : assigned
 institutions ||--o{ user_institutions : assigns
 users ||--o{ review_decisions : reasons
 import_batches ||--o{ import_rows : stages
 import_batches ||--|| import_jobs : checkpoints
 import_rows ||--o{ import_errors : explains
 audit_chains ||--o{ audit_events : sequences
```

The system audit chain has a nullable institution. Student program/profile values may be absent for incomplete imports. Officer assignments are many-to-many; administrator access never becomes an institution impersonation.
