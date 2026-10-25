from datetime import date
from decimal import Decimal
import hashlib
import random
from app.core.algorithms import CATALOGUE, money_round
from app.core.files import contained, root_path
from app.settings import settings
from db.seed.copy_load import copy_rows
from db.seed.fixtures import uid, pdf_bytes


def allocate(total, weights):
    quotas = {code: total * weight // 100 for code, weight in weights}
    remaining = total - sum(quotas.values())
    order = sorted(weights, key=lambda pair: (-(total * pair[1] % 100), pair[0]))
    for code, _ in order[:remaining]:
        quotas[code] += 1
    return quotas


def performances(conn):
    rng = random.Random(2026263)
    weighted = Decimal(0)
    credits_total = 0
    previous = None
    with conn.cursor(name="seed_completed_terms") as cursor:
        cursor.execute(
            "SELECT id,student_id,academic_year,term_no,term_type FROM enrolments ORDER BY student_id,term_no"
        )
        while True:
            chunk = cursor.fetchmany(10000)
            if not chunk:
                break
            rows = []
            for entry in chunk:
                sid = entry["student_id"]
                if sid != previous:
                    weighted = Decimal(0)
                    credits_total = 0
                    previous = sid
                credit = (
                    22
                    if sid == uid("student", 1)
                    else rng.randint(20, 26)
                    if entry["term_type"] == "SEMESTER"
                    else rng.randint(16, 22)
                )
                sgpa = money_round(max(0, min(10, rng.gauss(7.2, 1.4))))
                weighted += sgpa * credit
                credits_total += credit
                rows.append(
                    (
                        sid,
                        entry["id"],
                        entry["academic_year"],
                        entry["term_no"],
                        entry["term_type"],
                        credit,
                        sgpa,
                        money_round(weighted / credits_total),
                    )
                )
            copy_rows(
                conn,
                "academic_performance",
                "student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa",
                rows,
            )


def enrich(conn, count):
    rng = random.Random(2026263)
    showcase = uid("student", 1)
    people = conn.execute("SELECT id,institution_id,full_name FROM students ORDER BY id").fetchall()
    candidates = [p["id"] for p in people if p["id"] != showcase]

    def owners(percent):
        return {showcase, *rng.sample(candidates, max(0, count * percent // 100 - 1))}

    projects, internships, skilled, achievements, scholarships = [owners(p) for p in [10, 5, 30, 2, 2]]
    copy_rows(
        conn,
        "projects",
        "id,student_id,title,description,technologies,start_date,end_date",
        (
            (
                uid("project", "enrichment:" + str(sid)),
                sid,
                "Synthetic academic analysis",
                "A synthetic course project with reproducible evidence.",
                ["Python", "SQL"],
                date(2025, 1, 1),
                date(2025, 6, 1),
            )
            for sid in sorted(projects, key=str)
            if sid != showcase
        ),
    )
    copy_rows(
        conn,
        "internships",
        "id,student_id,organization,role,start_date,end_date,verified_locally",
        (
            (
                uid("internship", "enrichment:" + str(sid)),
                sid,
                "Synthetic Learning Lab",
                "Research intern",
                date(2025, 6, 1),
                date(2025, 8, 1),
                True,
            )
            for sid in sorted(internships, key=str)
            if sid != showcase
        ),
    )
    copy_rows(
        conn,
        "achievements",
        "id,student_id,title,awarded_by,awarded_on,description",
        (
            (
                uid("achievement", "enrichment:" + str(sid)),
                sid,
                "Synthetic project award",
                "Demo Learning Council",
                date(2026, 1, 1),
                "Synthetic academic recognition.",
            )
            for sid in sorted(achievements, key=str)
            if sid != showcase
        ),
    )
    copy_rows(
        conn,
        "scholarships",
        "id,student_id,name,academic_year,amount_inr,status",
        (
            (
                uid("scholarship", "enrichment:" + str(sid)),
                sid,
                "Synthetic learning scholarship",
                2025,
                5000 + (sid.int % 20) * 1000,
                "AWARDED",
            )
            for sid in sorted(scholarships, key=str)
            if sid != showcase
        ),
    )
    codes = list(dict.fromkeys(code for role in CATALOGUE.values() for code in role))
    for code in codes:
        conn.execute(
            "INSERT INTO skills(code,label,category) VALUES (%s,%s,%s) ON CONFLICT(code) DO NOTHING",
            (code, code.replace("_", " ").title(), "Career catalogue"),
        )
    skill_ids = {r["code"]: r["id"] for r in conn.execute("SELECT id,code FROM skills").fetchall()}
    skill_rows = []
    for sid in sorted(skilled, key=str):
        if sid == showcase:
            continue
        kind = "PROJECT" if sid in projects else "INTERNSHIP" if sid in internships else "SELF_REPORTED"
        evidence = (
            uid("project", "enrichment:" + str(sid))
            if kind == "PROJECT"
            else uid("internship", "enrichment:" + str(sid))
            if kind == "INTERNSHIP"
            else None
        )
        for code in rng.sample(codes, rng.randint(1, 3)):
            skill_rows.append((sid, skill_ids[code], rng.randint(2, 5), kind, evidence))
    copy_rows(conn, "student_skills", "student_id,skill_id,proficiency,evidence_kind,evidence_id", skill_rows)
    sample_ids = [showcase] + [
        r["student_id"]
        for r in conn.execute(
            "SELECT DISTINCT student_id FROM academic_performance WHERE student_id<>%s ORDER BY student_id LIMIT 100",
            (showcase,),
        ).fetchall()
    ]
    subjects = []
    for performance in conn.execute(
        "SELECT id,credits,sgpa FROM academic_performance WHERE student_id=ANY(%s::uuid[])", (sample_ids,)
    ).fetchall():
        total = int(performance["credits"])
        base = total // 4
        for index in range(4):
            credit = base + (1 if index < total % 4 else 0)
            subjects.append(
                (
                    performance["id"],
                    f"SYN-SUB-{index + 1:02d}",
                    f"Synthetic subject {index + 1}",
                    credit,
                    performance["sgpa"],
                )
            )
    copy_rows(conn, "performance_subjects", "performance_id,subject_code,subject_name,credits,grade_points", subjects)
    ncert = {100000: 200, 50000: 100, 5000: 20}.get(count, 2)
    certificate_owners = set(rng.sample(candidates, min(ncert, len(candidates))))
    for index, person in enumerate((p for p in people if p["id"] in certificate_owners), 1):
        cid = uid("certificate", "enrichment:" + str(person["id"]))
        data = pdf_bytes(
            name=person["full_name"], title="Synthetic Academic Foundations", credential=f"SDA-{1000000 + index:08d}"
        )
        key = f"{person['institution_id']}/{person['id']}/{cid}.pdf"
        path = contained(root_path(settings.storage_root), key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        conn.execute(
            "INSERT INTO certificates(id,student_id,title,issuer,issued_on,credential_id,storage_key,file_sha256,mime_type,purpose,acceptance_status,created_by) VALUES (%s,%s,'Synthetic Academic Foundations','Shiksham Demo Academy','2026-06-20',%s,%s,%s,'application/pdf','PASSPORT','PENDING',%s)",
            (
                cid,
                person["id"],
                f"SDA-{1000000 + index:08d}",
                key,
                hashlib.sha256(data).hexdigest(),
                uid("user", "officer"),
            ),
        )
    return dict(
        project_owners=len(projects),
        internship_owners=len(internships),
        skill_owners=len(skilled),
        achievement_owners=len(achievements),
        scholarship_owners=len(scholarships),
        other_certificate_files=len(certificate_owners),
        subject_sample_students=len(sample_ids),
    )
