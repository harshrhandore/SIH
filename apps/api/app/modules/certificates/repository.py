"""Fixed SQL for certificates transactions."""

from app.db.session import one


def persist_report_certificate_verifications(conn, params=()):
    return conn.execute(
        "INSERT INTO certificate_verifications(id,certificate_id,idempotency_key,ocr_engine,extraction_source,extracted_json,match_scores,confidence,verdict,risk,risk_score,reasons,file_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        params,
    )


def persist_report_certificates(conn, params=()):
    return conn.execute(
        "UPDATE certificates SET processing_status='DONE',issuer=%s,credential_id=%s WHERE id=%s", params
    )


def seed_certificates_students(conn, params=()):
    return one(conn, "SELECT * FROM students WHERE id=%s", params)


def seed_certificates_certificates(conn, params=()):
    return conn.execute(
        "INSERT INTO certificates(id,student_id,title,storage_key,file_sha256,mime_type,purpose,acceptance_status,created_by) VALUES (%s,%s,%s,%s,%s,'application/pdf','PASSPORT','ACCEPTED',%s)",
        params,
    )


def seed_certificates_certificates_2(conn, params=()):
    return one(conn, "SELECT * FROM certificates WHERE id=%s", params)


def work_certificates(conn, params=()):
    return one(conn, "SELECT id FROM certificates WHERE student_id=%s AND file_sha256=%s AND purpose=%s", params)


def work_certificates_2(conn, params=()):
    return conn.execute(
        "INSERT INTO certificates(id,student_id,title,storage_key,file_sha256,mime_type,purpose,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        params,
    )


def verify_certificate_locked_certificates(conn, params=()):
    return one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", params)


def verify_certificate_locked_certificate_verifications(conn, params=()):
    return one(conn, "SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s", params)


def verify_certificate_locked_certificates_2(conn, params=()):
    return conn.execute(
        "UPDATE certificates SET processing_status='PROCESSING',processing_started_at=now() WHERE id=%s", params
    )


def verify_certificate_locked_certificates_3(conn, params=()):
    return one(conn, "SELECT 1 FROM certificates WHERE file_sha256=%s AND student_id<>%s LIMIT 1", params)


def verify_certificate_locked_certificates_4(conn, params=()):
    return one(
        conn,
        "SELECT 1 FROM certificates WHERE lower(issuer)=lower(%s) AND lower(credential_id)=lower(%s) AND student_id<>%s LIMIT 1",
        params,
    )


def verify_certificate_locked_certificates_5(conn, params=()):
    return one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", params)


def verify_certificate_locked_certificate_verifications_2(conn, params=()):
    return one(conn, "SELECT * FROM certificate_verifications WHERE certificate_id=%s AND idempotency_key=%s", params)


def verify_certificate_locked_certificates_6(conn, params=()):
    return conn.execute("UPDATE certificates SET processing_status='FAILED' WHERE id=%s", params)


def report_certificate_verifications(conn, params=()):
    return one(conn, "SELECT * FROM certificate_verifications WHERE id=%s", params)


def report_certificates(conn, params=()):
    return one(conn, "SELECT * FROM certificates WHERE id=%s", params)


def certificate_file_certificates(conn, params=()):
    return one(conn, "SELECT * FROM certificates WHERE id=%s", params)


def acceptance_certificates(conn, params=()):
    return one(conn, "SELECT * FROM certificates WHERE id=%s FOR UPDATE", params)


def acceptance_certificate_verifications(conn, params=()):
    return one(
        conn, "SELECT * FROM certificate_verifications WHERE certificate_id=%s ORDER BY created_at DESC LIMIT 1", params
    )


def acceptance_certificates_2(conn, params=()):
    return conn.execute(
        "UPDATE certificates SET acceptance_status=%s,reviewed_at=now(),reviewed_by=%s,resolution_reason=%s WHERE id=%s",
        params,
    )
