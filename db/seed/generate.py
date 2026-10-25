"""Deterministic synthetic generator using bounded COPY buffers."""

import random
from datetime import date
from decimal import Decimal
from time import perf_counter

from app.core.algorithms import academic_cgpas, normalized_name, synthetic_id
from app.core.audit import append
from app.core.security import password_hash
from faker import Faker

from db.seed.fixtures import generate, reference, uid


def copy_rows(conn, table, columns, rows):
    with conn.cursor().copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)


def seed(conn, count, password):
    started = perf_counter()
    manifest = generate()
    rng = random.Random(2026263)
    fake = Faker("en_IN")
    fake.seed_instance(2026263)
    for role, label in [
        ("OPERATOR", "College Operator"),
        ("OFFICER", "Verification Officer"),
        ("ADMIN", "AICTE Administrator"),
        ("STUDENT", "Student"),
    ]:
        conn.execute("INSERT INTO roles VALUES (%s,%s)", (role, label))
    states = [
        "Karnataka",
        "Maharashtra",
        "Tamil Nadu",
        "Telangana",
        "Gujarat",
        "Delhi",
        "Uttar Pradesh",
        "West Bengal",
        "Karnataka",
        "Maharashtra",
        "Tamil Nadu",
        "Telangana",
    ]
    a_count = {100000: 9000, 50000: 4500, 5000: 1000}.get(count, max(80, count // 4))
    remain = count - a_count
    sizes = [a_count] + [remain // 11 + (1 if i < remain % 11 else 0) for i in range(11)]
    institutions = []
    programs = {}
    for i, n in enumerate(sizes):
        inst = uid("institution", i)
        institutions.append(inst)
        management = i >= 10
        expected = n + ({100000: 2000, 50000: 1500, 5000: 1500}.get(count, 1000) if i == 0 else 1000)
        conn.execute(
            "INSERT INTO institutions(id,aicte_code,name,state,institution_type,expected_records) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                inst,
                f"SYN-AICTE-{i + 1:03d}",
                "Synthetic Vidya Institute" if i == 0 else f"Synthetic Institute {i + 1:02d}",
                states[i],
                "MANAGEMENT" if management else "MIXED",
                expected,
            ),
        )
        weights = (
            [("PGDM:GENERAL", 100)]
            if management
            else [
                ("BTECH:CSE", 50),
                ("BTECH:ECE", 15),
                ("BTECH:ME", 10),
                ("BTECH:IT", 10),
                ("BTECH:AI&DS", 10),
                ("PGDM:GENERAL", 5),
            ]
        )
        allocated = 0
        for k, (code, w) in enumerate(weights):
            level, branch = code.split(":")
            pid = uid("program", f"{i}:{code}")
            conn.execute(
                "INSERT INTO programs(id,institution_id,level,name,branch,duration_years,term_type,total_terms,intake) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,100)",
                (
                    pid,
                    inst,
                    level,
                    ("B.Tech " if level == "BTECH" else "PGDM ") + branch,
                    branch,
                    4 if level == "BTECH" else 2,
                    "SEMESTER" if level == "BTECH" else "TRIMESTER",
                    8 if level == "BTECH" else 6,
                ),
            )
            exp = expected - allocated if k == len(weights) - 1 else expected * w // 100
            allocated += exp
            conn.execute("INSERT INTO program_expected_records VALUES (%s,%s)", (pid, exp))
            programs[(i, code)] = pid
        conn.execute(
            "INSERT INTO audit_chains(id,institution_id,name) VALUES (%s,%s,%s)",
            (uid("chain", i), inst, f"Synthetic institution {i + 1}"),
        )
        conn.execute("INSERT INTO institution_epochs(institution_id) VALUES (%s)", (inst,))
    encoded = password_hash(password)
    accounts = [
        ("operator_a", "operator.a@example.test", "OPERATOR", institutions[0], None),
        ("operator_b", "operator.b@example.test", "OPERATOR", institutions[1], None),
        ("officer", "officer@example.test", "OFFICER", None, None),
        ("admin", "admin@example.test", "ADMIN", None, None),
    ]
    for key, email, role, inst, student in accounts:
        conn.execute(
            "INSERT INTO users(id,email,password_hash,full_name,role_code,institution_id,student_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (uid("user", key), email, encoded, "Demo " + key.replace("_", " ").title(), role, inst, student),
        )
    for inst in institutions:
        conn.execute("INSERT INTO user_institutions VALUES (%s,%s)", (uid("user", "officer"), inst))

    def students():
        counter = 0
        for i, n in enumerate(sizes):
            for local in range(n):
                counter += 1
                if counter <= 71:
                    ref = reference(counter)
                    name, dob, parent = ref["full_name"], ref["dob"], ref["parent_name"]
                else:
                    name = fake.name()
                    if normalized_name(name) == "riya sharma":
                        name = "Synthetic " + name
                    dob = date(rng.randint(1999, 2007), rng.randint(1, 12), rng.randint(1, 28))
                    parent = None
                weight = local % 100
                code = (
                    "PGDM:GENERAL"
                    if i >= 10 or weight >= 95
                    else "BTECH:CSE"
                    if weight < 50
                    else "BTECH:ECE"
                    if weight < 65
                    else "BTECH:ME"
                    if weight < 75
                    else "BTECH:IT"
                    if weight < 85
                    else "BTECH:AI&DS"
                )
                if counter <= 71:
                    code = "BTECH:CSE"
                duration = 2 if code.startswith("PGDM") else 4
                admission = 2022 + local % 5
                year = min(duration, 2026 - admission + 1)
                status = "GRADUATED" if admission + duration <= 2026 else "ACTIVE"
                yield (
                    uid("student", counter),
                    institutions[i],
                    programs[(i, code)],
                    synthetic_id(counter),
                    synthetic_id(counter),
                    f"SYN-{chr(65 + i)}-{counter:06d}",
                    f"SYN-{chr(65 + i)}-{counter:06d}",
                    name,
                    normalized_name(name),
                    normalized_name(name),
                    parent,
                    dob,
                    "UNDISCLOSED",
                    "riya.sharma@example.test" if counter == 1 else f"synthetic.{counter}@example.test",
                    admission,
                    year,
                    status,
                    "ERP",
                    "PASSED_LOCAL_CHECKS",
                )

    copy_rows(
        conn,
        "students",
        "id,institution_id,program_id,apaar_id,submitted_apaar_id,enrollment_no,submitted_enrollment_no,full_name,normalized_name,transliterated_name,parent_name,dob,gender,email,admission_year,current_year,status,source,data_quality_status",
        students(),
    )
    conn.execute(
        "INSERT INTO users(id,email,password_hash,full_name,role_code,institution_id,student_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (
            uid("user", "student"),
            "student.riya@example.test",
            encoded,
            "Riya Sharma",
            "STUDENT",
            institutions[0],
            uid("student", 1),
        ),
    )
    conn.execute(
        "INSERT INTO enrolments(student_id,program_id,academic_year,term_no,term_type) SELECT s.id,s.program_id,s.admission_year+(t-1)/CASE WHEN p.term_type='SEMESTER' THEN 2 ELSE 3 END,t,p.term_type FROM students s JOIN programs p ON p.id=s.program_id CROSS JOIN LATERAL generate_series(1,CASE WHEN s.status='GRADUATED' THEN p.total_terms ELSE greatest(0,least(p.total_terms-1,(s.current_year-1)*CASE WHEN p.term_type='SEMESTER' THEN 2 ELSE 3 END)) END) t"
    )
    conn.execute(
        "INSERT INTO academic_performance(student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa) SELECT student_id,id,academic_year,term_no,term_type,22,round((5.0+(abs(hashtext(student_id::text||term_no::text)::bigint)%450)/100.0)::numeric,2),7 FROM enrolments"
    )
    conn.execute(
        "WITH c AS (SELECT id,round(sum(sgpa*credits) OVER (PARTITION BY student_id ORDER BY term_no)/sum(credits) OVER (PARTITION BY student_id ORDER BY term_no),2) AS val FROM academic_performance) UPDATE academic_performance ap SET cgpa=c.val FROM c WHERE c.id=ap.id"
    )
    showcase = uid("student", 1)
    sgpas = ["8.20", "8.30", "8.40", "8.50", "8.10", "8.60", "8.70", "8.56"]
    cgpas = academic_cgpas([(v, 22) for v in sgpas])
    for term, (sgpa, cgpa) in enumerate(zip(sgpas, cgpas), 1):
        conn.execute(
            "UPDATE academic_performance SET sgpa=%s,cgpa=%s WHERE student_id=%s AND term_no=%s",
            (Decimal(sgpa), cgpa, showcase, term),
        )
    conn.execute(
        "INSERT INTO record_versions(student_id,version_no,snapshot,changed_fields,changed_by,reason) SELECT id,1,jsonb_build_object('id',id,'full_name',full_name,'apaar_id',apaar_id,'data_quality_status',data_quality_status),'{}'::jsonb,%s,'Initial synthetic seed snapshot.' FROM students",
        (uid("user", "operator_a"),),
    )
    conn.execute(
        "INSERT INTO placements(student_id,company,role,package_lpa,placement_year,offer_status) SELECT s.id,'Synthetic Placement Co','Graduate Analyst',round((2.5+(abs(hashtext(s.id::text)::bigint)%2550)/100.0)::numeric,2),s.admission_year+p.duration_years,'OFFERED' FROM students s JOIN programs p ON p.id=s.program_id WHERE s.current_year=p.duration_years AND abs(hashtext(s.id::text)::bigint)%100<65"
    )
    project = uid("project", "showcase")
    conn.execute(
        "INSERT INTO projects VALUES (%s,%s,'Synthetic placement analytics','Analyzed synthetic placement outcomes.',ARRAY['Python','SQL','Pandas'],'2025-01-01','2025-06-01')",
        (project, showcase),
    )
    conn.execute(
        "INSERT INTO projects VALUES (%s,%s,'Student learning ledger','A synthetic learning record application.',ARRAY['Python','SQL'],'2025-07-01','2025-12-01')",
        (uid("project", "ledger"), showcase),
    )
    conn.execute(
        "INSERT INTO internships VALUES (%s,%s,'Synthetic Insights Lab','Data intern','2025-06-01','2025-08-01',true)",
        (uid("internship", 1), showcase),
    )
    conn.execute(
        "INSERT INTO achievements VALUES (%s,%s,'Synthetic analytics challenge','Demo Academy','2026-01-01','Synthetic project recognition.')",
        (uid("achievement", 1), showcase),
    )
    conn.execute(
        "INSERT INTO scholarships VALUES (%s,%s,'Synthetic merit award',2025,10000,'AWARDED')",
        (uid("scholarship", 1), showcase),
    )
    for code in ["PYTHON", "SQL", "STATISTICS", "PANDAS", "DATA_VISUALIZATION"]:
        sk = conn.execute(
            "INSERT INTO skills(code,label,category) VALUES (%s,%s,%s) RETURNING id",
            (code, code.replace("_", " ").title(), "Data"),
        ).fetchone()["id"]
        conn.execute("INSERT INTO student_skills VALUES (%s,%s,3,'PROJECT',%s)", (showcase, sk, project))
    case = uid("case", "showcase")
    conn.execute(
        "INSERT INTO review_cases(id,student_id,opened_reason,status) VALUES (%s,%s,'Seeded synthetic source review','APPROVED')",
        (case, showcase),
    )
    conn.execute(
        "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,'APPROVE','Rechecked the synthetic showcase source record.',1)",
        (case, uid("user", "officer")),
    )
    for i, inst in enumerate(institutions):
        append(
            conn,
            inst,
            uid("user", "officer"),
            "SEED_LOADED",
            "institution",
            inst,
            "Loaded deterministic synthetic baseline.",
            dict(students=sizes[i]),
        )
    append(
        conn,
        institutions[0],
        uid("user", "officer"),
        "REVIEW_APPROVED",
        "case",
        case,
        "Rechecked the synthetic showcase source record.",
        dict(student_version=1),
        showcase,
    )
    manifest["dataset_students"] = count
    manifest["institution_counts"] = sizes
    manifest["seed_seconds"] = round(perf_counter() - started, 3)
    return manifest
