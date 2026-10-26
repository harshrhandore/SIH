"""Fixed SQL for imports transactions."""

from app.db.session import one, many


def queue_batch(conn, params):
    return conn.execute("UPDATE import_batches SET status='QUEUED' WHERE id=%s", params)


def recover_and_list_queued(conn):
    interrupted = many(
        conn,
        "UPDATE import_jobs SET status='FAILED',error_code='PROCESS_INTERRUPTED',error_message='Process interrupted; retry from saved checkpoint.',updated_at=now() WHERE status='RUNNING' AND coalesce(heartbeat_at,updated_at)<now()-interval '60 seconds' AND pg_try_advisory_xact_lock(hashtextextended(id::text,26263)) RETURNING batch_id",
    )
    if interrupted:
        conn.execute(
            "UPDATE import_batches SET status='FAILED' WHERE id=ANY(%s::uuid[])",
            ([row["batch_id"] for row in interrupted],),
        )
    return many(conn, "SELECT id FROM import_jobs WHERE status='QUEUED' ORDER BY created_at,id LIMIT 10")


def upload_import_batches(conn, params=()):
    return conn.execute(
        "INSERT INTO import_batches(id,institution_id,uploader_id,filename,storage_key,file_sha256,total_rows) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        params,
    )


def upload_import_rows(conn, params=()):
    return conn.execute("INSERT INTO import_rows(batch_id,row_no,raw_data) VALUES (%s,%s,%s)", params)


def start_students(conn, params=()):
    return many(
        conn,
        "SELECT id,submitted_apaar_id,submitted_enrollment_no,full_name,parent_name,dob FROM students WHERE institution_id=%s",
        params,
    )


def start_students_2(conn, params=()):
    return many(conn, "SELECT id,apaar_id FROM students WHERE apaar_id IS NOT NULL", params)


def start_import_batches(conn, params=()):
    return conn.execute("UPDATE import_batches SET status='QUEUED',reference_snapshot=%s WHERE id=%s", params)


def start_import_jobs(conn, params=()):
    return conn.execute("INSERT INTO import_jobs(id,batch_id,status) VALUES (%s,%s,'QUEUED')", params)


def process_import_jobs(conn, params=()):
    return one(conn, "SELECT * FROM import_jobs WHERE id=%s AND status='QUEUED' FOR UPDATE SKIP LOCKED", params)


def process_import_jobs_2(conn, params=()):
    return conn.execute("UPDATE import_jobs SET status='RUNNING',heartbeat_at=now() WHERE id=%s", params)


def process_import_batches(conn, params=()):
    return one(conn, "SELECT * FROM import_batches WHERE id=%s", params)


def process_import_batches_2(conn, params=()):
    return conn.execute(
        "UPDATE import_batches SET status='RUNNING',started_at=coalesce(started_at,now()) WHERE id=%s", params
    )


def process_programs(conn, params=()):
    return many(conn, "SELECT *,level||':'||branch AS code FROM programs WHERE institution_id=%s", params)


def process_import_rows(conn, params=()):
    return many(conn, "SELECT * FROM import_rows WHERE batch_id=%s ORDER BY row_no", params)


def process_query(conn, params=()):
    return conn.execute("SELECT pg_advisory_xact_lock(26263,8)", params)


def process_import_jobs_3(conn, params=()):
    return one(conn, "SELECT * FROM import_jobs WHERE id=%s FOR UPDATE", params)


def process_students(conn, params=()):
    return one(conn, "SELECT id FROM students WHERE apaar_id=%s AND id<>%s", params)


def process_students_2(conn, params=()):
    return one(
        conn,
        "SELECT id,submitted_enrollment_no,full_name,parent_name,dob FROM students WHERE institution_id=%s AND enrollment_no=%s AND id<>%s",
        params,
    )


def process_students_3(conn, params=()):
    return conn.execute(
        "INSERT INTO students(id,institution_id,program_id,apaar_id,submitted_apaar_id,enrollment_no,submitted_enrollment_no,full_name,normalized_name,transliterated_name,parent_name,dob,email,admission_year,current_year,source,data_quality_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'CSV',%s)",
        params,
    )


def process_import_rows_2(conn, params=()):
    return conn.execute(
        "UPDATE import_rows SET student_id=%s,normalized_data=%s,status=%s WHERE batch_id=%s AND row_no=%s", params
    )


def process_verification_checks(conn, params=()):
    return conn.execute(
        "INSERT INTO verification_checks(code,description,severity,version) VALUES (%s,%s,%s,1) ON CONFLICT DO NOTHING",
        params,
    )


def process_verification_findings(conn, params=()):
    return conn.execute(
        "INSERT INTO verification_findings(student_id,check_code,rule_version,student_version,batch_id,row_no,severity,explanation,evidence) VALUES (%s,%s,1,1,%s,%s,%s,%s,%s)",
        params,
    )


def process_import_errors(conn, params=()):
    return conn.execute(
        "INSERT INTO import_errors(batch_id,row_no,field,code,message,is_primary,evidence) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        params,
    )


def process_review_cases(conn, params=()):
    return conn.execute("INSERT INTO review_cases(student_id,opened_reason) VALUES (%s,%s)", params)


def process_duplicate_candidates(conn, params=()):
    return conn.execute(
        "INSERT INTO duplicate_candidates(student_a,student_b,match_type,score,matched_fields) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        params,
    )


def process_record_versions(conn, params=()):
    return conn.execute(
        "INSERT INTO record_versions(student_id,version_no,snapshot,changed_fields,changed_by,reason) VALUES (%s,1,%s,%s,%s,%s)",
        params,
    )


def process_enrolments(conn, params=()):
    return one(
        conn,
        "INSERT INTO enrolments(student_id,program_id,academic_year,term_no,term_type) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        params,
    )


def process_academic_performance(conn, params=()):
    return conn.execute(
        "INSERT INTO academic_performance(student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        params,
    )


def process_import_rows_3(conn, params=()):
    return one(
        conn,
        "SELECT count(*) FILTER(WHERE status='CLEAN') AS clean,count(*) FILTER(WHERE status='FLAGGED') AS flagged,count(*) FILTER(WHERE status='INCOMPLETE') AS incomplete FROM import_rows WHERE batch_id=%s",
        params,
    )


def process_import_batches_3(conn, params=()):
    return conn.execute(
        "UPDATE import_batches SET processed_rows=%s,clean_rows=%s,flagged_rows=%s,incomplete_rows=%s WHERE id=%s",
        params,
    )


def process_import_jobs_4(conn, params=()):
    return conn.execute("UPDATE import_jobs SET next_row=%s,progress=%s,heartbeat_at=now() WHERE id=%s", params)


def process_import_jobs_5(conn, params=()):
    return conn.execute("UPDATE import_jobs SET status='COMPLETED',progress=100,updated_at=now() WHERE id=%s", params)


def process_import_batches_4(conn, params=()):
    return conn.execute("UPDATE import_batches SET status='COMPLETED',finished_at=now() WHERE id=%s", params)


def process_query_2(conn, params=()):
    return conn.execute("SELECT refresh_demo_views()", params)


def process_import_jobs_6(conn, params=()):
    return conn.execute(
        "UPDATE import_jobs SET status='FAILED',error_code='PROCESS_INTERRUPTED',error_message='Import interrupted; retry from saved checkpoint.',updated_at=now() WHERE id=%s",
        params,
    )


def process_import_batches_5(conn, params=()):
    return conn.execute(
        "UPDATE import_batches SET status='FAILED' WHERE id=(SELECT batch_id FROM import_jobs WHERE id=%s)", params
    )


def report_import_batches(conn, params=()):
    return one(conn, "SELECT * FROM import_batches WHERE id=%s", params)


def report_import_errors(conn, params=()):
    return many(
        conn,
        "SELECT code,count(*)::int AS count FROM import_errors WHERE batch_id=%s AND is_primary GROUP BY code ORDER BY code",
        params,
    )


def report_import_errors_2(conn, params=()):
    return one(conn, "SELECT count(*) AS n FROM import_errors WHERE batch_id=%s", params)


def list_imports_import_batches(conn, params=()):
    return one(
        conn,
        "SELECT count(*) AS n FROM import_batches WHERE (%s::uuid[] IS NULL OR institution_id=ANY(%s::uuid[]))",
        params,
    )


def import_detail_import_rows(conn, params=()):
    return many(
        conn,
        "SELECT row_no,raw_data,normalized_data,status FROM import_rows WHERE batch_id=%s ORDER BY row_no LIMIT 20",
        params,
    )


def import_detail_import_jobs(conn, params=()):
    return one(conn, "SELECT * FROM import_jobs WHERE batch_id=%s", params)


def set_mapping_import_rows(conn, params=()):
    return many(conn, "SELECT row_no,raw_data FROM import_rows WHERE batch_id=%s ORDER BY row_no LIMIT 20", params)


def set_mapping_import_batches(conn, params=()):
    return conn.execute("UPDATE import_batches SET status='MAPPED',column_mapping=%s WHERE id=%s", params)


def get_job_import_jobs(conn, params=()):
    return one(conn, "SELECT * FROM import_jobs WHERE id=%s", params)


def retry_job_import_jobs(conn, params=()):
    return one(conn, "SELECT * FROM import_jobs WHERE id=%s FOR UPDATE", params)


def retry_job_import_jobs_2(conn, params=()):
    return conn.execute(
        "UPDATE import_jobs SET status='QUEUED',retry_count=retry_count+1,error_code=NULL,error_message=NULL WHERE id=%s",
        params,
    )


def errors_csv_import_errors(conn, params=()):
    return many(
        conn,
        "SELECT row_no,field,code,is_primary,message,evidence FROM import_errors WHERE batch_id=%s ORDER BY row_no,id",
        params,
    )
