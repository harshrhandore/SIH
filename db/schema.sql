CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE institutions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 aicte_code text NOT NULL UNIQUE,
 name text NOT NULL,
 state text NOT NULL,
 institution_type text NOT NULL CHECK (institution_type IN ('ENGINEERING','MANAGEMENT','MIXED')),
 status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),
 expected_records integer NOT NULL CHECK (expected_records > 0),
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK (aicte_code LIKE 'SYN-%')
);
CREATE TABLE programs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES institutions,
 level text NOT NULL CHECK (level IN ('BTECH','PGDM')),
 name text NOT NULL,
 branch text NOT NULL,
 duration_years smallint NOT NULL CHECK (duration_years IN (2,4)),
 term_type text NOT NULL CHECK (term_type IN ('SEMESTER','TRIMESTER')),
 total_terms smallint NOT NULL CHECK (total_terms IN (6,8)),
 intake integer NOT NULL CHECK (intake > 0),
 UNIQUE (institution_id,level,branch),
 UNIQUE (id,institution_id),
 CHECK ((level='BTECH' AND duration_years=4 AND total_terms=8 AND term_type='SEMESTER')
     OR (level='PGDM' AND duration_years=2 AND total_terms=6 AND term_type='TRIMESTER'))
);
CREATE TABLE roles (
 code text PRIMARY KEY CHECK (code IN ('OPERATOR','OFFICER','ADMIN','STUDENT')),
 label text NOT NULL
);
CREATE TABLE users (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 email text NOT NULL,
 password_hash text NOT NULL,
 full_name text NOT NULL,
 role_code text NOT NULL REFERENCES roles(code),
 institution_id uuid REFERENCES institutions,
 student_id uuid,
 active boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK ((role_code='OPERATOR' AND institution_id IS NOT NULL AND student_id IS NULL)
     OR (role_code='STUDENT' AND institution_id IS NOT NULL AND student_id IS NOT NULL)
     OR (role_code IN ('OFFICER','ADMIN') AND institution_id IS NULL AND student_id IS NULL))
);
CREATE UNIQUE INDEX ux_users_email ON users(lower(email));
CREATE TABLE user_institutions (
 user_id uuid NOT NULL REFERENCES users,
 institution_id uuid NOT NULL REFERENCES institutions,
 PRIMARY KEY (user_id,institution_id)
);
CREATE TABLE students (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES institutions,
 program_id uuid,
 apaar_id text,
 submitted_apaar_id text,
 enrollment_no text,
 submitted_enrollment_no text,
 full_name text,
 normalized_name text NOT NULL DEFAULT '',
 transliterated_name text NOT NULL DEFAULT '',
 parent_name text,
 dob date,
 gender text CHECK (gender IN ('FEMALE','MALE','OTHER','UNDISCLOSED')),
 email text,
 admission_year smallint CHECK (admission_year BETWEEN 1950 AND 2100),
 current_year smallint CHECK (current_year BETWEEN 1 AND 4),
 status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','GRADUATED','WITHDRAWN')),
 source text NOT NULL CHECK (source IN ('ERP','CSV','MANUAL')),
 data_quality_status text NOT NULL DEFAULT 'INCOMPLETE'
   CHECK (data_quality_status IN ('PASSED_LOCAL_CHECKS','FLAGGED_FOR_REVIEW','INCOMPLETE')),
 external_status text NOT NULL DEFAULT 'EXTERNAL_VERIFICATION_PENDING'
   CHECK (external_status IN ('EXTERNAL_VERIFICATION_PENDING','MOCK_MATCH','MOCK_NO_MATCH')),
 version_no integer NOT NULL DEFAULT 1 CHECK (version_no > 0),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (id,institution_id),
 UNIQUE (id,program_id),
 FOREIGN KEY (program_id,institution_id) REFERENCES programs(id,institution_id),
 CHECK (apaar_id IS NULL OR apaar_id ~ '^SYN-[0-9]{13}$'),
 CHECK (enrollment_no IS NULL OR length(enrollment_no) BETWEEN 3 AND 64)
);
CREATE UNIQUE INDEX ux_students_apaar ON students(apaar_id) WHERE apaar_id IS NOT NULL;
CREATE UNIQUE INDEX ux_students_enrollment ON students(institution_id,enrollment_no) WHERE enrollment_no IS NOT NULL;
CREATE INDEX ix_students_scope_program_year ON students(institution_id,program_id,current_year,id)
 INCLUDE (full_name,apaar_id,data_quality_status);
CREATE INDEX ix_students_enrollment_lookup ON students(enrollment_no) WHERE enrollment_no IS NOT NULL;
CREATE INDEX ix_students_name_trgm ON students USING gin(normalized_name gin_trgm_ops);
CREATE INDEX ix_students_name_translit_trgm ON students USING gin(transliterated_name gin_trgm_ops);
CREATE INDEX ix_students_dob ON students(institution_id,dob) WHERE dob IS NOT NULL;
ALTER TABLE users ADD CONSTRAINT fk_user_student_scope
 FOREIGN KEY (student_id,institution_id) REFERENCES students(id,institution_id);

CREATE TABLE enrolments (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 student_id uuid NOT NULL,
 program_id uuid NOT NULL,
 academic_year smallint NOT NULL CHECK (academic_year BETWEEN 1950 AND 2100),
 term_no smallint NOT NULL CHECK (term_no BETWEEN 1 AND 8),
 term_type text NOT NULL CHECK (term_type IN ('SEMESTER','TRIMESTER')),
 UNIQUE (student_id,term_no),
 FOREIGN KEY (student_id,program_id) REFERENCES students(id,program_id)
);
CREATE TABLE academic_performance (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 student_id uuid NOT NULL REFERENCES students,
 enrolment_id bigint NOT NULL UNIQUE REFERENCES enrolments,
 academic_year smallint NOT NULL CHECK (academic_year BETWEEN 1950 AND 2100),
 term_no smallint NOT NULL CHECK (term_no BETWEEN 1 AND 8),
 term_type text NOT NULL CHECK (term_type IN ('SEMESTER','TRIMESTER')),
 credits numeric(5,1) NOT NULL CHECK (credits > 0 AND credits <= 60),
 sgpa numeric(4,2) NOT NULL CHECK (sgpa BETWEEN 0 AND 10),
 cgpa numeric(4,2) NOT NULL CHECK (cgpa BETWEEN 0 AND 10),
 UNIQUE (student_id,term_no)
);
CREATE INDEX ix_performance_student_term ON academic_performance(student_id,term_no DESC) INCLUDE (cgpa,sgpa,credits);
CREATE TABLE performance_subjects (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 performance_id bigint NOT NULL REFERENCES academic_performance,
 subject_code text NOT NULL,
 subject_name text NOT NULL,
 credits numeric(4,1) NOT NULL CHECK (credits > 0 AND credits <= 20),
 grade_points numeric(4,2) NOT NULL CHECK (grade_points BETWEEN 0 AND 10),
 UNIQUE (performance_id,subject_code)
);
CREATE TABLE placements (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 company text NOT NULL,
 role text NOT NULL,
 package_lpa numeric(7,2) NOT NULL CHECK (package_lpa BETWEEN 0 AND 500),
 placement_year smallint NOT NULL CHECK (placement_year BETWEEN 1950 AND 2100),
 offer_status text NOT NULL CHECK (offer_status IN ('OFFERED','ACCEPTED','DECLINED','REVOKED')),
 UNIQUE (student_id,company,role,placement_year)
);
CREATE INDEX ix_placement_student_year ON placements(student_id,placement_year);
CREATE TABLE certificates (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 title text NOT NULL,
 issuer text,
 issued_on date,
 credential_id text,
 storage_key text NOT NULL,
 file_sha256 text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
 mime_type text NOT NULL CHECK (mime_type IN ('application/pdf','image/png','image/jpeg')),
 purpose text NOT NULL DEFAULT 'PASSPORT' CHECK (purpose IN ('PASSPORT','TRIAL')),
 acceptance_status text NOT NULL DEFAULT 'PENDING' CHECK (acceptance_status IN ('PENDING','ACCEPTED','REJECTED')),
 created_by uuid NOT NULL REFERENCES users,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_certificate_sha ON certificates(file_sha256);
CREATE INDEX ix_certificate_student ON certificates(student_id,purpose,acceptance_status);
CREATE INDEX ix_certificate_credential ON certificates(lower(issuer),lower(credential_id)) WHERE credential_id IS NOT NULL;
CREATE TABLE projects (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 title text NOT NULL,
 description text NOT NULL,
 technologies text[] NOT NULL DEFAULT '{}',
 start_date date NOT NULL,
 end_date date,
 CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE TABLE internships (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 organization text NOT NULL,
 role text NOT NULL,
 start_date date NOT NULL,
 end_date date,
 verified_locally boolean NOT NULL DEFAULT false,
 CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE TABLE skills (
 id smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 code text NOT NULL UNIQUE,
 label text NOT NULL,
 category text NOT NULL
);
CREATE TABLE student_skills (
 student_id uuid NOT NULL REFERENCES students,
 skill_id smallint NOT NULL REFERENCES skills,
 proficiency smallint NOT NULL CHECK (proficiency BETWEEN 1 AND 5),
 evidence_kind text NOT NULL CHECK (evidence_kind IN ('PROJECT','CERTIFICATE','INTERNSHIP','SELF_REPORTED')),
 evidence_id uuid,
 PRIMARY KEY (student_id,skill_id)
);
CREATE TABLE achievements (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 title text NOT NULL,
 awarded_by text NOT NULL,
 awarded_on date NOT NULL,
 description text NOT NULL DEFAULT ''
);
CREATE TABLE scholarships (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 name text NOT NULL,
 academic_year smallint NOT NULL CHECK (academic_year BETWEEN 1950 AND 2100),
 amount_inr numeric(12,2) NOT NULL CHECK (amount_inr >= 0),
 status text NOT NULL CHECK (status IN ('AWARDED','DISBURSED','EXPIRED'))
);

CREATE TABLE refresh_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id uuid NOT NULL REFERENCES users,
 family_id uuid NOT NULL,
 token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
 csrf_hash text NOT NULL CHECK (csrf_hash ~ '^[0-9a-f]{64}$'),
 expires_at timestamptz NOT NULL,
 rotated_at timestamptz,
 revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_refresh_family ON refresh_sessions(family_id);
CREATE TABLE import_batches (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid NOT NULL REFERENCES institutions,
 uploader_id uuid NOT NULL REFERENCES users,
 filename text NOT NULL,
 storage_key text NOT NULL,
 file_sha256 text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
 status text NOT NULL DEFAULT 'UPLOADED' CHECK (status IN ('UPLOADED','MAPPED','QUEUED','RUNNING','COMPLETED','FAILED')),
 total_rows integer NOT NULL CHECK (total_rows BETWEEN 1 AND 100000),
 processed_rows integer NOT NULL DEFAULT 0 CHECK (processed_rows >= 0),
 clean_rows integer NOT NULL DEFAULT 0 CHECK (clean_rows >= 0),
 flagged_rows integer NOT NULL DEFAULT 0 CHECK (flagged_rows >= 0),
 incomplete_rows integer NOT NULL DEFAULT 0 CHECK (incomplete_rows >= 0),
 column_mapping jsonb NOT NULL DEFAULT '{}',
 reference_snapshot jsonb NOT NULL DEFAULT '{}',
 started_at timestamptz,
 finished_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (id,institution_id),
 CHECK (processed_rows <= total_rows),
 CHECK (clean_rows + flagged_rows + incomplete_rows <= processed_rows)
);
CREATE TABLE import_rows (
 batch_id uuid NOT NULL REFERENCES import_batches,
 row_no integer NOT NULL CHECK (row_no > 0),
 raw_data jsonb NOT NULL,
 normalized_data jsonb NOT NULL DEFAULT '{}',
 student_id uuid REFERENCES students,
 status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','CLEAN','FLAGGED','INCOMPLETE')),
 PRIMARY KEY (batch_id,row_no)
);
CREATE INDEX ix_import_rows_student ON import_rows(student_id);
CREATE TABLE import_errors (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 batch_id uuid NOT NULL,
 row_no integer NOT NULL,
 field text NOT NULL,
 code text NOT NULL,
 message text NOT NULL,
 is_primary boolean NOT NULL DEFAULT true,
 evidence jsonb NOT NULL DEFAULT '{}',
 FOREIGN KEY (batch_id,row_no) REFERENCES import_rows(batch_id,row_no),
 UNIQUE (batch_id,row_no,field,code)
);
CREATE TABLE import_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 batch_id uuid NOT NULL UNIQUE REFERENCES import_batches,
 status text NOT NULL CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
 progress numeric(5,2) NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
 next_row integer NOT NULL DEFAULT 1 CHECK (next_row > 0),
 retry_count smallint NOT NULL DEFAULT 0 CHECK (retry_count BETWEEN 0 AND 3),
 heartbeat_at timestamptz,
 error_code text,
 error_message text,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE verification_checks (
 code text PRIMARY KEY,
 description text NOT NULL,
 severity text NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR')),
 version integer NOT NULL CHECK (version > 0),
 enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE verification_findings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 check_code text NOT NULL REFERENCES verification_checks(code),
 rule_version integer NOT NULL CHECK (rule_version > 0),
 student_version integer NOT NULL CHECK (student_version > 0),
 batch_id uuid REFERENCES import_batches,
 row_no integer,
 severity text NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR')),
 explanation text NOT NULL,
 evidence jsonb NOT NULL,
 resolved_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (student_id,student_version,check_code)
);
CREATE INDEX ix_findings_open ON verification_findings(student_id) WHERE resolved_at IS NULL;
CREATE TABLE duplicate_candidates (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_a uuid NOT NULL REFERENCES students,
 student_b uuid NOT NULL REFERENCES students,
 match_type text NOT NULL CHECK (match_type IN ('EXACT','POSSIBLE')),
 score numeric(5,2) NOT NULL CHECK (score BETWEEN 0 AND 100),
 matched_fields jsonb NOT NULL,
 status text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','DISMISSED','CONFIRMED')),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (student_a,student_b),
 CHECK (student_a < student_b)
);
CREATE INDEX ix_duplicate_b ON duplicate_candidates(student_b);
CREATE TABLE review_cases (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 opened_reason text NOT NULL,
 status text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CORRECTION_REQUESTED','ESCALATED','APPROVED')),
 assignee_id uuid REFERENCES users,
 version_no integer NOT NULL DEFAULT 1 CHECK (version_no > 0),
 escalated_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_case_unresolved ON review_cases(student_id) WHERE status <> 'APPROVED';
CREATE INDEX ix_case_queue ON review_cases(status,created_at,id);
CREATE TABLE review_decisions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 case_id uuid NOT NULL REFERENCES review_cases,
 reviewer_id uuid NOT NULL REFERENCES users,
 action text NOT NULL CHECK (action IN ('APPROVE','REQUEST_CORRECTION','ESCALATE','CONFIRM_DUPLICATE','DISMISS_DUPLICATE','ACCESS_ESCALATED')),
 reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 10 AND 1000),
 case_version integer NOT NULL CHECK (case_version > 0),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE record_versions (
 student_id uuid NOT NULL REFERENCES students,
 version_no integer NOT NULL CHECK (version_no > 0),
 snapshot jsonb NOT NULL,
 changed_fields jsonb NOT NULL,
 changed_by uuid NOT NULL REFERENCES users,
 reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 10 AND 1000),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY (student_id,version_no)
);
CREATE TABLE certificate_verifications (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 certificate_id uuid NOT NULL REFERENCES certificates,
 idempotency_key uuid NOT NULL,
 ocr_text text NOT NULL DEFAULT '',
 ocr_engine text NOT NULL,
 extraction_source text NOT NULL CHECK (extraction_source IN ('GEMINI','RULE_BASED','PDF_TEXT','UNAVAILABLE')),
 extracted_json jsonb NOT NULL,
 match_scores jsonb NOT NULL,
 confidence numeric(5,2) NOT NULL CHECK (confidence BETWEEN 0 AND 100),
 verdict text NOT NULL CHECK (verdict IN ('VERIFIED_LOCAL','REJECTED','NEEDS_REVIEW','UNREADABLE')),
 risk text NOT NULL CHECK (risk IN ('low','medium','high')),
 risk_score smallint NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
 reasons jsonb NOT NULL,
 file_sha256 text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
 phash bit(64),
 formula_version integer NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (certificate_id,idempotency_key)
);
CREATE INDEX ix_cv_certificate_latest ON certificate_verifications(certificate_id,created_at DESC,id);
CREATE TABLE trust_scores (
 student_id uuid PRIMARY KEY REFERENCES students,
 score smallint NOT NULL CHECK (score BETWEEN 0 AND 100),
 components jsonb NOT NULL,
 formula_version integer NOT NULL DEFAULT 1,
 computed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE external_verifications (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 requested_by uuid NOT NULL REFERENCES users,
 adapter text NOT NULL CHECK (adapter='MockApaarAdapter'),
 status text NOT NULL CHECK (status IN ('MOCK_MATCH','MOCK_NO_MATCH')),
 official boolean NOT NULL DEFAULT false CHECK (official=false),
 evidence jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE career_sessions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 student_id uuid NOT NULL REFERENCES students,
 question text NOT NULL CHECK (length(question) BETWEEN 1 AND 1000),
 role_code text NOT NULL,
 response jsonb NOT NULL,
 phrasing_source text NOT NULL CHECK (phrasing_source IN ('GEMINI','RULE_BASED')),
 catalogue_version integer NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE analytics_refresh_state (
 view_name text PRIMARY KEY,
 refreshed_at timestamptz,
 status text NOT NULL CHECK (status IN ('NEVER','RUNNING','READY','FAILED')),
 error text
);
CREATE TABLE data_quality_snapshots (
 institution_id uuid NOT NULL REFERENCES institutions,
 snapshot_date date NOT NULL,
 total integer NOT NULL CHECK (total >= 0),
 clean integer NOT NULL CHECK (clean >= 0),
 flagged integer NOT NULL CHECK (flagged >= 0),
 incomplete integer NOT NULL CHECK (incomplete >= 0),
 PRIMARY KEY (institution_id,snapshot_date),
 CHECK (clean+flagged+incomplete=total)
);
CREATE TABLE app_state (
 seed_ready boolean NOT NULL DEFAULT false,
 singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
 updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO app_state(singleton) VALUES (true);
CREATE TABLE institution_epochs (
 institution_id uuid PRIMARY KEY REFERENCES institutions,
 data_epoch bigint NOT NULL DEFAULT 0 CHECK (data_epoch >= 0),
 updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION check_term_integrity() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p programs%ROWTYPE; e enrolments%ROWTYPE;
BEGIN
 SELECT pr.* INTO p FROM students s JOIN programs pr ON pr.id=s.program_id WHERE s.id=NEW.student_id;
 IF NOT FOUND THEN RAISE EXCEPTION 'PROGRAM_REQUIRED'; END IF;
 IF NEW.term_type <> p.term_type OR NEW.term_no > p.total_terms THEN
   RAISE EXCEPTION 'TERM_OUT_OF_RANGE';
 END IF;
 IF TG_TABLE_NAME='academic_performance' THEN
   SELECT * INTO e FROM enrolments WHERE id=NEW.enrolment_id;
   IF NOT FOUND OR e.student_id<>NEW.student_id OR e.term_no<>NEW.term_no
     OR e.term_type<>NEW.term_type OR e.academic_year<>NEW.academic_year THEN
     RAISE EXCEPTION 'ENROLMENT_MISMATCH';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER enrolment_term_guard BEFORE INSERT OR UPDATE ON enrolments
 FOR EACH ROW EXECUTE FUNCTION check_term_integrity();
CREATE TRIGGER performance_term_guard BEFORE INSERT OR UPDATE ON academic_performance
 FOR EACH ROW EXECUTE FUNCTION check_term_integrity();

CREATE FUNCTION protect_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'APPEND_ONLY'; END $$;
CREATE TRIGGER record_version_immutable BEFORE UPDATE OR DELETE ON record_versions
 FOR EACH ROW EXECUTE FUNCTION protect_history();
CREATE TRIGGER review_decision_immutable BEFORE UPDATE OR DELETE ON review_decisions
 FOR EACH ROW EXECUTE FUNCTION protect_history();

CREATE INDEX ix_students_quality ON students(institution_id,data_quality_status);
CREATE INDEX ix_students_admission ON students(institution_id,admission_year);
CREATE INDEX ix_students_raw_apaar ON students(submitted_apaar_id) WHERE submitted_apaar_id IS NOT NULL;
CREATE INDEX ix_students_raw_enrollment ON students(institution_id,submitted_enrollment_no) WHERE submitted_enrollment_no IS NOT NULL;
CREATE INDEX ix_import_batch_scope_time ON import_batches(institution_id,created_at DESC);
CREATE INDEX ix_findings_batch ON verification_findings(batch_id);
CREATE INDEX ix_case_student ON review_cases(student_id);
CREATE INDEX ix_record_version_time ON record_versions(student_id,created_at);
CREATE INDEX ix_career_student_time ON career_sessions(student_id,created_at DESC);
CREATE INDEX ix_project_student ON projects(student_id);
CREATE INDEX ix_internship_student ON internships(student_id);
CREATE INDEX ix_achievement_student ON achievements(student_id);
CREATE INDEX ix_scholarship_student ON scholarships(student_id);

CREATE TABLE api_idempotency (
 actor_id uuid NOT NULL REFERENCES users,
 key uuid NOT NULL,
 operation text NOT NULL,
 request_hash text NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
 response_status smallint NOT NULL CHECK (response_status BETWEEN 200 AND 299),
 response_body jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(actor_id,key)
);
CREATE INDEX ix_idempotency_expiry ON api_idempotency(created_at);

CREATE TABLE program_expected_records (
 program_id uuid PRIMARY KEY REFERENCES programs,
 expected_records integer NOT NULL CHECK (expected_records > 0)
);

ALTER TABLE certificates ADD COLUMN reviewed_at timestamptz;
ALTER TABLE certificates ADD COLUMN reviewed_by uuid REFERENCES users;
ALTER TABLE certificates ADD COLUMN resolution_reason text;
ALTER TABLE certificates ADD CONSTRAINT ck_certificate_review
 CHECK ((reviewed_at IS NULL AND reviewed_by IS NULL AND resolution_reason IS NULL)
 OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL AND length(btrim(resolution_reason)) BETWEEN 10 AND 1000));
ALTER TABLE certificates ADD COLUMN processing_status text NOT NULL DEFAULT 'IDLE'
 CHECK (processing_status IN ('IDLE','PROCESSING','DONE','FAILED'));
ALTER TABLE certificates ADD COLUMN processing_started_at timestamptz;
CREATE TABLE benchmark_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 requested_by uuid NOT NULL REFERENCES users,
 status text NOT NULL CHECK (status IN ('RUNNING','COMPLETED','FAILED')),
 result jsonb,
 created_at timestamptz NOT NULL DEFAULT now(),
 finished_at timestamptz
);

CREATE TABLE audit_chains (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 institution_id uuid UNIQUE REFERENCES institutions,
 name text NOT NULL,
 head_seq bigint NOT NULL DEFAULT 0 CHECK (head_seq >= 0),
 head_hash text NOT NULL DEFAULT repeat('0',64) CHECK (head_hash ~ '^[0-9a-f]{64}$')
);
CREATE UNIQUE INDEX ux_system_audit_chain ON audit_chains((1)) WHERE institution_id IS NULL;
CREATE TABLE audit_events (
 chain_id uuid NOT NULL REFERENCES audit_chains,
 sequence_no bigint NOT NULL CHECK (sequence_no > 0),
 id uuid NOT NULL UNIQUE,
 institution_id uuid REFERENCES institutions,
 student_id uuid REFERENCES students,
 actor_id uuid NOT NULL REFERENCES users,
 action text NOT NULL,
 entity_type text NOT NULL,
 entity_id text NOT NULL,
 reason text NOT NULL,
 occurred_at timestamptz NOT NULL,
 payload jsonb NOT NULL,
 canonical_text text NOT NULL CHECK (jsonb_typeof(canonical_text::jsonb)='object'),
 prev_hash text NOT NULL CHECK (prev_hash ~ '^[0-9a-f]{64}$'),
 row_hash text NOT NULL CHECK (row_hash ~ '^[0-9a-f]{64}$'),
 PRIMARY KEY (chain_id,sequence_no)
);
CREATE INDEX ix_audit_student_time ON audit_events(student_id,occurred_at,sequence_no);
CREATE INDEX ix_audit_scope_time ON audit_events(institution_id,occurred_at DESC);
CREATE TRIGGER audit_event_immutable BEFORE UPDATE OR DELETE ON audit_events
 FOR EACH ROW EXECUTE FUNCTION protect_history();
CREATE TRIGGER audit_event_no_truncate BEFORE TRUNCATE ON audit_events
 FOR EACH STATEMENT EXECUTE FUNCTION protect_history();

CREATE FUNCTION append_audit(p_chain uuid,p_canonical text)
RETURNS TABLE(sequence_no bigint,row_hash text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c audit_chains%ROWTYPE; e jsonb; next_seq bigint; next_hash text;
BEGIN
 SELECT * INTO c FROM audit_chains WHERE id=p_chain FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'AUDIT_CHAIN_NOT_FOUND'; END IF;
 e := p_canonical::jsonb;
 next_seq := c.head_seq+1;
 IF e->>'chain_id' IS DISTINCT FROM p_chain::text
   OR (e->>'sequence_no')::bigint IS DISTINCT FROM next_seq
   OR (e->>'institution_id')::uuid IS DISTINCT FROM c.institution_id THEN
   RAISE EXCEPTION 'AUDIT_ENVELOPE_MISMATCH';
 END IF;
 IF NOT (e ?& ARRAY['event_id','chain_id','sequence_no','institution_id','student_id',
    'actor_id','action','entity_type','entity_id','reason','occurred_at','payload']) THEN
   RAISE EXCEPTION 'AUDIT_FIELDS_MISSING';
 END IF;
 IF (SELECT count(*) FROM jsonb_object_keys(e)) <> 12 THEN
   RAISE EXCEPTION 'AUDIT_EXTRA_FIELDS';
 END IF;
 IF jsonb_typeof(e->'payload')<>'object' THEN RAISE EXCEPTION 'AUDIT_PAYLOAD_INVALID'; END IF;
 IF (e->>'student_id') IS NOT NULL AND NOT EXISTS (
   SELECT 1 FROM students s WHERE s.id=(e->>'student_id')::uuid AND s.institution_id=c.institution_id
 ) THEN RAISE EXCEPTION 'AUDIT_STUDENT_SCOPE'; END IF;
 next_hash := encode(digest(convert_to(c.head_hash||p_canonical,'UTF8'),'sha256'),'hex');
 INSERT INTO audit_events(chain_id,sequence_no,id,institution_id,student_id,actor_id,
   action,entity_type,entity_id,reason,occurred_at,payload,canonical_text,prev_hash,row_hash)
 VALUES(p_chain,next_seq,(e->>'event_id')::uuid,c.institution_id,(e->>'student_id')::uuid,
   (e->>'actor_id')::uuid,e->>'action',e->>'entity_type',e->>'entity_id',e->>'reason',
   (e->>'occurred_at')::timestamptz,e->'payload',p_canonical,c.head_hash,next_hash);
 UPDATE audit_chains SET head_seq=next_seq,head_hash=next_hash WHERE id=p_chain;
 RETURN QUERY SELECT next_seq,next_hash;
END $$;
REVOKE ALL ON FUNCTION append_audit(uuid,text) FROM PUBLIC;

CREATE FUNCTION lock_audit_chain(p_institution uuid) RETURNS SETOF audit_chains
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
BEGIN
 RETURN QUERY SELECT * FROM audit_chains WHERE institution_id IS NOT DISTINCT FROM p_institution FOR UPDATE;
END $$;
REVOKE ALL ON FUNCTION lock_audit_chain(uuid) FROM PUBLIC;

CREATE MATERIALIZED VIEW mv_admissions AS
SELECT s.institution_id,s.program_id,s.admission_year AS year,count(*)::integer AS admitted
FROM students s
WHERE s.program_id IS NOT NULL AND s.admission_year IS NOT NULL
GROUP BY s.institution_id,s.program_id,s.admission_year;
CREATE UNIQUE INDEX ux_mv_admissions ON mv_admissions(institution_id,program_id,year);

CREATE MATERIALIZED VIEW mv_placements AS
WITH eligible AS (
 SELECT s.id,s.institution_id,s.program_id,
        (s.admission_year+p.duration_years)::smallint AS year
 FROM students s JOIN programs p ON p.id=s.program_id
 WHERE s.current_year=p.duration_years AND s.status<>'WITHDRAWN' AND s.admission_year IS NOT NULL
), best_offer AS (
 SELECT e.id,e.institution_id,e.program_id,e.year,
        max(pl.package_lpa) FILTER (WHERE pl.offer_status IN ('OFFERED','ACCEPTED')) AS package
 FROM eligible e LEFT JOIN placements pl ON pl.student_id=e.id AND pl.placement_year=e.year
 GROUP BY e.id,e.institution_id,e.program_id,e.year
)
SELECT institution_id,program_id,year,count(*)::integer AS eligible_students,
 count(package)::integer AS placed_students,
 round(100.0*count(package)/nullif(count(*),0),2) AS placement_rate,
 percentile_cont(0.5) WITHIN GROUP (ORDER BY package) FILTER (WHERE package IS NOT NULL) AS median_package_lpa,
 max(package) AS max_package_lpa
FROM best_offer GROUP BY institution_id,program_id,year;
CREATE UNIQUE INDEX ux_mv_placements ON mv_placements(institution_id,program_id,year);

CREATE MATERIALIZED VIEW mv_performance AS
WITH yearly AS (
 SELECT ap.student_id,ap.academic_year AS year,
   bool_and(ap.sgpa>=4) AS passed_all_terms,
   (array_agg(ap.cgpa ORDER BY ap.term_no DESC))[1] AS latest_cgpa
 FROM academic_performance ap GROUP BY ap.student_id,ap.academic_year
)
SELECT s.institution_id,s.program_id,p.branch,y.year,count(*)::integer AS assessed_students,
 round(avg(y.latest_cgpa),2) AS avg_cgpa,
 round(100.0*count(*) FILTER (WHERE y.passed_all_terms)/nullif(count(*),0),2) AS pass_percent,
 count(*) FILTER (WHERE y.latest_cgpa<4)::integer AS bucket_0_4,
 count(*) FILTER (WHERE y.latest_cgpa>=4 AND y.latest_cgpa<6)::integer AS bucket_4_6,
 count(*) FILTER (WHERE y.latest_cgpa>=6 AND y.latest_cgpa<8)::integer AS bucket_6_8,
 count(*) FILTER (WHERE y.latest_cgpa>=8)::integer AS bucket_8_10
FROM yearly y JOIN students s ON s.id=y.student_id JOIN programs p ON p.id=s.program_id
GROUP BY s.institution_id,s.program_id,p.branch,y.year;
CREATE UNIQUE INDEX ux_mv_performance ON mv_performance(institution_id,program_id,branch,year);

CREATE MATERIALIZED VIEW mv_data_quality AS
SELECT i.id AS institution_id,i.expected_records,count(s.id)::integer AS total,
 count(s.id) FILTER (WHERE s.data_quality_status='PASSED_LOCAL_CHECKS')::integer AS clean,
 count(s.id) FILTER (WHERE s.data_quality_status='FLAGGED_FOR_REVIEW')::integer AS flagged,
 count(s.id) FILTER (WHERE s.data_quality_status='INCOMPLETE')::integer AS incomplete,
 count(s.id) FILTER (WHERE s.external_status='EXTERNAL_VERIFICATION_PENDING')::integer AS external_pending,
 least(100.0,round(100.0*count(s.id)/i.expected_records,2)) AS submission_percent,
 greatest(0,i.expected_records-count(s.id))::integer AS missing_records,
 (SELECT count(*)::integer FROM review_cases rc JOIN students rs ON rs.id=rc.student_id
   WHERE rs.institution_id=i.id AND rc.status<>'APPROVED') AS pending_reviews
FROM institutions i LEFT JOIN students s ON s.institution_id=i.id
GROUP BY i.id,i.expected_records;
CREATE UNIQUE INDEX ux_mv_quality ON mv_data_quality(institution_id);

INSERT INTO analytics_refresh_state(view_name,status)
VALUES ('mv_admissions','NEVER'),('mv_placements','NEVER'),('mv_performance','NEVER'),('mv_data_quality','NEVER');

ALTER TABLE analytics_refresh_state ADD COLUMN source_epoch bigint NOT NULL DEFAULT 0;
CREATE FUNCTION refresh_demo_views() RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE v_epoch bigint; v_stamp timestamptz;
BEGIN
 IF NOT pg_try_advisory_xact_lock(26263,4) THEN RETURN false; END IF;
 SELECT COALESCE(sum(data_epoch),0) INTO v_epoch FROM institution_epochs;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_admissions;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_placements;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_performance;
 REFRESH MATERIALIZED VIEW CONCURRENTLY mv_data_quality;
 v_stamp:=clock_timestamp();
 UPDATE analytics_refresh_state SET status='READY',refreshed_at=v_stamp,source_epoch=v_epoch,error=NULL;
 INSERT INTO data_quality_snapshots(institution_id,snapshot_date,total,clean,flagged,incomplete)
 SELECT institution_id,(v_stamp AT TIME ZONE 'Asia/Kolkata')::date,total,clean,flagged,incomplete
 FROM mv_data_quality
 ON CONFLICT(institution_id,snapshot_date) DO UPDATE
 SET total=EXCLUDED.total,clean=EXCLUDED.clean,flagged=EXCLUDED.flagged,incomplete=EXCLUDED.incomplete;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION refresh_demo_views() FROM PUBLIC;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO shiksham_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO shiksham_runtime;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO shiksham_runtime;
REVOKE ALL ON audit_events,audit_chains FROM shiksham_runtime;
GRANT SELECT ON audit_events,audit_chains TO shiksham_runtime;
REVOKE UPDATE,DELETE,TRUNCATE ON record_versions,review_decisions FROM shiksham_runtime;
GRANT SELECT,INSERT ON record_versions,review_decisions TO shiksham_runtime;
GRANT EXECUTE ON FUNCTION append_audit(uuid,text) TO shiksham_runtime;
GRANT EXECUTE ON FUNCTION lock_audit_chain(uuid) TO shiksham_runtime;
GRANT EXECUTE ON FUNCTION refresh_demo_views() TO shiksham_runtime;

