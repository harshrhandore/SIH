from app.db.session import one, many
from psycopg.types.json import Jsonb


def save_session(conn, session_id, student_id, question, role, result):
    conn.execute(
        "INSERT INTO career_sessions(id,student_id,question,role_code,response,phrasing_source) VALUES (%s,%s,%s,%s,%s,'RULE_BASED')",
        (session_id, student_id, question, role, Jsonb(result)),
    )


def history(conn, student_id, limit, offset):
    rows = many(
        conn,
        "SELECT id AS session_id,question,role_code,(response->>'readiness_percent')::int AS readiness_percent,response,created_at FROM career_sessions WHERE student_id=%s ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s",
        (student_id, limit, offset),
    )
    total = one(conn, "SELECT count(*) AS n FROM career_sessions WHERE student_id=%s", (student_id,))["n"]
    return rows, total


def evidenced_skills(conn, sid):
    rows = many(
        conn,
        "SELECT sk.code,sk.label,ss.* FROM student_skills ss JOIN skills sk ON sk.id=ss.skill_id WHERE ss.student_id=%s AND ss.proficiency>=2",
        (sid,),
    )
    result = {}
    for row in rows:
        table = {"PROJECT": "projects", "CERTIFICATE": "certificates", "INTERNSHIP": "internships"}.get(
            row["evidence_kind"]
        )
        if not table:
            continue
        evidence = one(conn, f"SELECT * FROM {table} WHERE id=%s AND student_id=%s", (row["evidence_id"], sid))
        if evidence and (table != "certificates" or evidence["acceptance_status"] == "ACCEPTED"):
            result[row["code"]] = [
                dict(
                    kind=row["evidence_kind"],
                    id=str(evidence["id"]),
                    title=evidence.get("title") or evidence.get("organization"),
                )
            ]
    return result
