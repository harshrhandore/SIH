import hashlib
from app.core.algorithms import valid_id
from app.core.files import read
from app.db.session import one, many


def validate_seed(conn, count):
    if one(conn, "SELECT count(*) AS n FROM students")["n"] != count:
        raise RuntimeError("SEED_COUNT_MISMATCH")
    if one(
        conn,
        "SELECT 1 FROM institutions i JOIN programs p ON p.institution_id=i.id JOIN program_expected_records e ON e.program_id=p.id GROUP BY i.id HAVING sum(e.expected_records)<>i.expected_records LIMIT 1",
    ):
        raise RuntimeError("PROGRAM_EXPECTATIONS_MISMATCH")
    if not all(valid_id(row["apaar_id"]) for row in many(conn, "SELECT apaar_id FROM students")):
        raise RuntimeError("SEED_IDENTIFIER_INVALID")
    completed = one(conn, "SELECT count(DISTINCT student_id) AS n FROM academic_performance")["n"]
    if completed < count * 0.75:
        raise RuntimeError("COMPLETED_TERM_COVERAGE")
    if one(
        conn,
        "SELECT 1 FROM (SELECT ap.cgpa,round(sum(ap.sgpa*ap.credits) OVER (PARTITION BY student_id ORDER BY term_no)/sum(ap.credits) OVER (PARTITION BY student_id ORDER BY term_no),2) AS expected FROM academic_performance ap) q WHERE cgpa<>expected LIMIT 1",
    ):
        raise RuntimeError("CREDIT_WEIGHTED_CGPA_MISMATCH")
    measured = {}
    for table, percentage in [
        ("projects", 10),
        ("internships", 5),
        ("student_skills", 30),
        ("achievements", 2),
        ("scholarships", 2),
    ]:
        actual = one(conn, f"SELECT count(DISTINCT student_id) AS n FROM {table}")["n"]
        if actual != count * percentage // 100:
            raise RuntimeError("ENRICHMENT_COUNT_MISMATCH:" + table)
        measured[table + "_owners"] = actual
    files = many(conn, "SELECT storage_key,file_sha256 FROM certificates")
    expected_files = {100000: 202, 50000: 102, 5000: 22, 200: 4}[count]
    if len(files) != expected_files:
        raise RuntimeError("CERTIFICATE_SUBSET_COUNT")
    size = 0
    for file in files:
        data = read(file["storage_key"]).read_bytes()
        size += len(data)
        if hashlib.sha256(data).hexdigest() != file["file_sha256"]:
            raise RuntimeError("CERTIFICATE_FILE_HASH")
    return {
        "completed_term_students": completed,
        "certificate_files": len(files),
        "certificate_storage_bytes": size,
        **measured,
    }
