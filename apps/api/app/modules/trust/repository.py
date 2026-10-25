from psycopg.types.json import Jsonb
from app.db.session import one, many
from app.modules.career.repository import evidenced_skills


def inputs(conn, student):
    sid = student["id"]
    terms = many(conn, "SELECT term_no FROM academic_performance WHERE student_id=%s", (sid,))
    skills = evidenced_skills(conn, sid)
    findings = many(
        conn,
        "SELECT check_code,severity FROM verification_findings WHERE student_id=%s AND resolved_at IS NULL",
        (sid,),
    )
    certificates = many(
        conn,
        "SELECT c.*,v.verdict,v.confidence,v.risk_score FROM certificates c LEFT JOIN LATERAL (SELECT * FROM certificate_verifications WHERE certificate_id=c.id ORDER BY created_at DESC,id DESC LIMIT 1) v ON true WHERE c.student_id=%s AND c.purpose='PASSPORT'",
        (sid,),
    )
    approved = one(
        conn,
        "SELECT 1 FROM review_cases c JOIN review_decisions d ON d.case_id=c.id WHERE c.student_id=%s AND c.status='APPROVED' AND d.action='APPROVE' AND (SELECT max(version_no) FROM record_versions WHERE student_id=%s AND created_at<=d.created_at)=%s AND NOT EXISTS(SELECT 1 FROM review_cases WHERE student_id=%s AND status<>'APPROVED') LIMIT 1",
        (sid, sid, student["version_no"], sid),
    )
    return terms, skills, findings, certificates, approved


def persist(conn, student_id, result):
    conn.execute(
        "INSERT INTO trust_scores(student_id,score,components) VALUES (%s,%s,%s) ON CONFLICT(student_id) DO UPDATE SET score=EXCLUDED.score,components=EXCLUDED.components,computed_at=now()",
        (student_id, result["score"], Jsonb(result)),
    )
