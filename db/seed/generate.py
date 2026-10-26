"""Deterministic synthetic generator using bounded COPY buffers."""

import random
from datetime import date
from decimal import Decimal
from time import perf_counter

from app.core.algorithms import academic_cgpas, normalized_name, synthetic_id
from app.core.audit import append
from app.core.security import password_hash
from faker import Faker
from unidecode import unidecode

from db.seed.fixtures import generate, reference, uid
from db.seed.copy_load import copy_rows
from db.seed.enrichment import allocate, performances, enrich


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
    sizes = [a_count] + [
        remain // 11 + (1 if i < remain % 11 else 0) for i in range(11)
    ]
    institutions = []
    programs = {}
    program_slots = {}
    for i, n in enumerate(sizes):
        inst = uid("institution", i)
        institutions.append(inst)
        management = i >= 10
        expected = n + (
            {100000: 2000, 50000: 1500, 5000: 1500}.get(count, 1000) if i == 0 else 1000
        )
        conn.execute(
            "INSERT INTO institutions(id,aicte_code,name,state,institution_type,expected_records) VALUES (%s,%s,%s,%s,%s,%s)",
            (
                inst,
                f"SYN-AICTE-{i + 1:03d}",
                "Synthetic Vidya Institute"
                if i == 0
                else f"Synthetic Institute {i + 1:02d}",
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
        expected_allocations = allocate(expected, weights)
        actual_allocations = allocate(n, weights)
        program_slots[i] = [
            code for code, _ in weights for _ in range(actual_allocations[code])
        ]
        for k, (code, w) in enumerate(weights):
            level, branch = code.split(":")
            pid = uid("program", f"{i}:{code}")
            conn.execute(
                "INSERT INTO programs(id,institution_id,level,name,branch,duration_years,term_type,total_terms,intake) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,100)",
                (
                    pid,
                    inst,
                    level,
                    (
                        "B.Tech "
                        + {
                            "CSE": "Computer Science",
                            "ECE": "Electronics and Communication",
                            "ME": "Mechanical Engineering",
                            "IT": "Information Technology",
                            "AI&DS": "Artificial Intelligence and Data Science",
                        }[branch]
                    )
                    if level == "BTECH"
                    else "PGDM General Management",
                    branch,
                    4 if level == "BTECH" else 2,
                    "SEMESTER" if level == "BTECH" else "TRIMESTER",
                    8 if level == "BTECH" else 6,
                ),
            )
            exp = expected_allocations[code]
            conn.execute(
                "INSERT INTO program_expected_records VALUES (%s,%s)", (pid, exp)
            )
            programs[(i, code)] = pid
        conn.execute(
            "INSERT INTO audit_chains(id,institution_id,name) VALUES (%s,%s,%s)",
            (uid("chain", i), inst, f"Synthetic institution {i + 1}"),
        )
        conn.execute(
            "INSERT INTO institution_epochs(institution_id) VALUES (%s)", (inst,)
        )
    encoded = password_hash(password)
    conn.execute(
        "INSERT INTO audit_chains(id,institution_id,name) VALUES (%s,NULL,'Synthetic system')",
        (uid("chain", "system"),),
    )
    accounts = [
        ("operator_a", "operator.a@example.test", "OPERATOR", institutions[0], None),
        ("operator_b", "operator.b@example.test", "OPERATOR", institutions[1], None),
        ("officer", "officer@example.test", "OFFICER", None, None),
        ("admin", "admin@example.test", "ADMIN", None, None),
    ]
    for key, email, role, inst, student in accounts:
        conn.execute(
            "INSERT INTO users(id,email,password_hash,full_name,role_code,institution_id,student_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (
                uid("user", key),
                email,
                encoded,
                "Demo " + key.replace("_", " ").title(),
                role,
                inst,
                student,
            ),
        )
    for inst in institutions:
        conn.execute(
            "INSERT INTO user_institutions VALUES (%s,%s)",
            (uid("user", "officer"), inst),
        )

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
                    if "riya sharma" in normalized_name(name):
                        name = f"Synthetic Reserved Learner {counter}"
                    dob = date(
                        rng.randint(1999, 2007), rng.randint(1, 12), rng.randint(1, 28)
                    )
                    parent = None
                code = program_slots[i][local]
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
                    unidecode(normalized_name(name)),
                    parent,
                    dob,
                    "UNDISCLOSED",
                    "riya.sharma@example.test"
                    if counter == 1
                    else f"synthetic.{counter}@example.test",
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
    performances(conn)
    showcase = uid("student", 1)
    sgpas = ["8.20", "8.30", "8.40", "8.50", "8.10", "8.60", "8.70", "8.56"]
    cgpas = academic_cgpas([(v, 22) for v in sgpas])
    for term, (sgpa, cgpa) in enumerate(zip(sgpas, cgpas), 1):
        conn.execute(
            "UPDATE academic_performance SET sgpa=%s,cgpa=%s WHERE student_id=%s AND term_no=%s",
            (Decimal(sgpa), cgpa, showcase, term),
        )
    conn.execute(
        "INSERT INTO record_versions(student_id,version_no,snapshot,changed_fields,changed_by,reason) SELECT s.id,1,jsonb_build_object('id',s.id,'institution_id',s.institution_id,'program_id',s.program_id,'full_name',s.full_name,'apaar_id',s.apaar_id,'submitted_apaar_id',s.submitted_apaar_id,'enrollment_no',s.enrollment_no,'submitted_enrollment_no',s.submitted_enrollment_no,'dob',s.dob,'email',s.email,'admission_year',s.admission_year,'current_year',s.current_year,'source',s.source,'data_quality_status',s.data_quality_status,'external_status',s.external_status,'terms',coalesce((SELECT jsonb_agg(jsonb_build_object('term_no',ap.term_no,'term_type',ap.term_type,'sgpa',ap.sgpa,'cgpa',ap.cgpa,'credits',ap.credits) ORDER BY ap.term_no) FROM academic_performance ap WHERE ap.student_id=s.id),'[]'::jsonb)),'{}'::jsonb,%s,'Initial synthetic seed snapshot.' FROM students s",
        (uid("user", "officer"),),
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
        conn.execute(
            "INSERT INTO student_skills VALUES (%s,%s,3,'PROJECT',%s)",
            (showcase, sk, project),
        )
    case = uid("case", "showcase")
    conn.execute(
        "INSERT INTO review_cases(id,student_id,opened_reason,status) VALUES (%s,%s,'Seeded synthetic source review','APPROVED')",
        (case, showcase),
    )
    conn.execute(
        "INSERT INTO review_decisions(case_id,reviewer_id,action,reason,case_version) VALUES (%s,%s,'APPROVE','Rechecked the synthetic showcase source record.',1)",
        (case, uid("user", "officer")),
    )
    manifest["enrichment"] = enrich(conn, count)
    manifest["program_counts"] = [
        dict(
            institution_id=str(row["institution_id"]),
            program_id=str(row["program_id"]),
            students=row["n"],
        )
        for row in conn.execute(
            "SELECT institution_id,program_id,count(*) AS n FROM students GROUP BY institution_id,program_id ORDER BY institution_id,program_id"
        ).fetchall()
    ]
    manifest["cohort_counts"] = [
        dict(admission_year=row["admission_year"], students=row["n"])
        for row in conn.execute(
            "SELECT admission_year,count(*) AS n FROM students GROUP BY admission_year ORDER BY admission_year"
        ).fetchall()
    ]
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
