"""Fixed SQL statements for verification transactions."""

from app.db.session import one, many


def checks_verification_findings(conn, params=()):
    return many(
        conn,
        "SELECT check_code AS code,severity,explanation FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL",
        params,
    )


def checks_institution_epochs(conn, params=()):
    return one(conn, "SELECT data_epoch FROM institution_epochs WHERE institution_id=%s", params)


def work_external_verifications(conn, params=()):
    return conn.execute(
        "INSERT INTO external_verifications(student_id,requested_by,adapter,status,evidence) VALUES (%s,%s,'MockApaarAdapter',%s,%s)",
        params,
    )


def work_students(conn, params=()):
    return conn.execute("UPDATE students SET external_status=%s WHERE id=%s", params)
