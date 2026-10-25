from collections import defaultdict
from datetime import datetime, date
from io import BytesIO, StringIO
import csv
from uuid import uuid4, uuid5
from typing import Any
from unidecode import unidecode
import re
import zipfile
from openpyxl import load_workbook
from psycopg.types.json import Jsonb
from app.core.algorithms import clean, valid_id, normalized_name, name_match, possible_match
from app.core.audit import append
from app.core.errors import fail
from app.core.files import store, read
from app.db.session import connect, one, many
from app.modules.students.service import jsonable, epoch

ALIASES = {
    "submitted_apaar_id": "APAAR ID",
    "submitted_enrollment_no": "Enrollment No",
    "full_name": "Student Name",
    "dob": "DOB",
    "parent_name": "Parent Name",
    "program_code": "Program",
    "admission_year": "Admission Year",
    "current_year": "Year",
    "term_no": "Semester",
    "sgpa": "SGPA",
    "credits": "Credits",
    "email": "Email",
    "gender": "Gender",
}
MANDATORY = {"submitted_enrollment_no", "full_name", "dob", "program_code", "admission_year", "current_year"}
PRIORITY = [
    "MISSING_MANDATORY",
    "MISSING_APAAR",
    "INVALID_APAAR",
    "DUPLICATE_APAAR",
    "NAME_INCONSISTENCY",
    "ENROLLMENT_CONFLICT",
    "IMPOSSIBLE_ACADEMIC",
    "POSSIBLE_DUPLICATE",
    "RECORD_ALREADY_EXISTS",
    "INVALID_DOB",
    "INVALID_EMAIL",
]
MESSAGES = {
    "MISSING_MANDATORY": "A mandatory field is missing.",
    "MISSING_APAAR": "Synthetic ID is missing.",
    "INVALID_APAAR": "Synthetic ID format/check digit is invalid.",
    "DUPLICATE_APAAR": "Synthetic ID is already claimed.",
    "NAME_INCONSISTENCY": "Submitted name differs from the reference enrollment.",
    "ENROLLMENT_CONFLICT": "Enrollment conflicts with an existing record.",
    "IMPOSSIBLE_ACADEMIC": "Academic values are outside program bounds.",
    "POSSIBLE_DUPLICATE": "Name and corroborating details suggest a possible duplicate.",
    "RECORD_ALREADY_EXISTS": "Matching source record already exists.",
    "INVALID_DOB": "Date of birth is future or outside the permitted admission age range.",
    "INVALID_EMAIL": "Email syntax is invalid.",
}


def parse(data, filename):
    if len(data) > 20 * 1024 * 1024:
        fail("FILE_TOO_LARGE", 413)
    if filename.lower().endswith(".xlsx"):
        try:
            archive = zipfile.ZipFile(BytesIO(data))
            if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
                fail("XLSX_EXPANSION_LIMIT")
            book = load_workbook(BytesIO(data), read_only=True, data_only=False, keep_links=False)
            nonempty = []
            for sheet in book:
                rows = list(sheet.iter_rows())
                if any(any(c.value is not None for c in row) for row in rows):
                    nonempty.append(rows)
            if len(nonempty) != 1:
                fail("WORKSHEET_SELECTION_REQUIRED")
            cells = nonempty[0]
            if any(c.data_type == "f" for row in cells for c in row):
                fail("XLSX_FORMULA_NOT_SUPPORTED")
            headers = [str(c.value or "") for c in cells[0]]
            rows = [{h: str(c.value) if c.value is not None else "" for h, c in zip(headers, row)} for row in cells[1:]]
        except (zipfile.BadZipFile, ValueError):
            fail("UNSUPPORTED_SPREADSHEET")
    elif filename.lower().endswith(".csv"):
        try:
            reader = csv.DictReader(StringIO(data.decode("utf-8-sig")))
            headers = list(reader.fieldnames or [])
            rows = list(reader)
        except (UnicodeDecodeError, csv.Error):
            fail("UNSUPPORTED_CSV")
    else:
        fail("UNSUPPORTED_MEDIA_TYPE", 415)
    if len(headers) > 100 or len(set(headers)) != len(headers):
        fail("INVALID_HEADERS")
    if not rows:
        fail("EMPTY_FILE")
    if len(rows) > 1000:
        fail("TOO_MANY_ROWS")
    return headers, rows


def upload(conn, user, data, filename, key):
    headers, rows = parse(data, filename)
    batch = uuid4()
    storage, sha = store(
        data, user["institution_id"], "imports", "xlsx" if filename.lower().endswith(".xlsx") else "csv"
    )
    conn.execute(
        "INSERT INTO import_batches(id,institution_id,uploader_id,filename,storage_key,file_sha256,total_rows) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (batch, user["institution_id"], user["id"], filename, storage, sha, len(rows)),
    )
    for i, row in enumerate(rows, 1):
        conn.execute("INSERT INTO import_rows(batch_id,row_no,raw_data) VALUES (%s,%s,%s)", (batch, i, Jsonb(row)))
    return dict(
        batch_id=batch,
        status="UPLOADED",
        total_rows=len(rows),
        headers=headers,
        preview=[dict(row_no=i + 1, values=row) for i, row in enumerate(rows[:20])],
        suggested_mapping={k: dict(column=v, confidence=100) for k, v in ALIASES.items() if v in headers},
    )


def normalized(raw, mapping, date_format="DD/MM/YYYY"):
    out = {k: clean(raw.get(column)) for k, column in mapping.items()}
    out["submitted_apaar_id"] = (out.get("submitted_apaar_id") or "").upper() or None
    out["submitted_enrollment_no"] = " ".join((out.get("submitted_enrollment_no") or "").upper().split()) or None
    try:
        value = out.get("dob")
        out["dob"] = (
            date.fromisoformat(value)
            if value and len(value) == 10 and value[4] == "-"
            else datetime.strptime(value, "%d/%m/%Y").date()
            if value and date_format == "DD/MM/YYYY"
            else None
        )
    except (ValueError, TypeError):
        out["dob"] = None
    return out


def make_indexes(rows, claims=None):
    by_id = {}
    by_enrollment = {}
    by_dob = defaultdict(list)
    for row in rows:
        if row.get("submitted_apaar_id"):
            by_id[row["submitted_apaar_id"]] = row
        if row.get("submitted_enrollment_no"):
            by_enrollment[row["submitted_enrollment_no"]] = row
        if row.get("dob"):
            by_dob[str(row["dob"])].append(row)
    for identifier, sid in (claims or {}).items():
        by_id.setdefault(identifier, dict(id=sid))
    return by_id, by_enrollment, by_dob


def evaluate(row, program, indexes):
    ids, enrollments, dobs = indexes
    findings: list[dict[str, Any]] = []
    candidates = []

    def add(code, field="record", value=None, secondary=False):
        if any(f["code"] == code for f in findings):
            return
        findings.append(
            dict(
                code=code,
                field=field,
                severity="WARNING"
                if code in {"NAME_INCONSISTENCY", "POSSIBLE_DUPLICATE", "RECORD_ALREADY_EXISTS"}
                else "ERROR",
                explanation=MESSAGES[code],
                is_primary=not secondary,
                evidence=dict(
                    field=field,
                    submitted_value=str(value) if value is not None else None,
                    expected=MESSAGES[code],
                    related_student_ids=[],
                ),
            )
        )

    missing = [k for k in MANDATORY if not row.get(k)]
    if missing:
        add("MISSING_MANDATORY", ",".join(missing))
    if row.get("dob"):
        dob = date.fromisoformat(str(row["dob"]))
        admission = date(int(row.get("admission_year") or 2026), 7, 1)
        age = admission.year - dob.year - ((admission.month, admission.day) < (dob.month, dob.day))
        if dob > date(2026, 10, 25) or not 14 <= age <= 80:
            add("INVALID_DOB", "dob", dob)
    if row.get("email") and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", row["email"]):
        add("INVALID_EMAIL", "email", row["email"])
    identifier = row.get("submitted_apaar_id")
    if not identifier:
        add("MISSING_APAAR", "submitted_apaar_id")
    elif not valid_id(identifier):
        add("INVALID_APAAR", "submitted_apaar_id", identifier)
    elif identifier in ids and str(ids[identifier]["id"]) != str(row.get("id")):
        add("DUPLICATE_APAAR", "submitted_apaar_id", identifier)
        candidates.append((ids[identifier]["id"], "EXACT", 100))
    enrollment = row.get("submitted_enrollment_no")
    existing = enrollments.get(enrollment)
    if existing and str(existing["id"]) != str(row.get("id")):
        same_dob = str(row.get("dob")) == str(existing.get("dob"))
        n, guard = name_match(row.get("full_name"), existing.get("full_name"))
        if (
            same_dob
            and normalized_name(row.get("full_name")) != normalized_name(existing.get("full_name"))
            and (70 <= n < 95 or not guard)
        ):
            add("NAME_INCONSISTENCY", "full_name", row.get("full_name"))
            add("ENROLLMENT_CONFLICT", "submitted_enrollment_no", enrollment, True)
        elif not same_dob or normalized_name(row.get("full_name")) != normalized_name(existing.get("full_name")):
            add("ENROLLMENT_CONFLICT", "submitted_enrollment_no", enrollment)
        else:
            add("RECORD_ALREADY_EXISTS", "submitted_enrollment_no", enrollment)
        candidates.append((existing["id"], "EXACT", 100))
    impossible = False
    try:
        if not program:
            impossible = True
        else:
            if row.get("current_year") and not 1 <= int(row["current_year"]) <= program["duration_years"]:
                impossible = True
            if row.get("admission_year") and not 1950 <= int(row["admission_year"]) <= 2026:
                impossible = True
            for field in ["sgpa", "cgpa"]:
                if row.get(field) and not 0 <= float(row[field]) <= 10:
                    impossible = True
            if row.get("term_no") and not 1 <= int(row["term_no"]) <= program["total_terms"]:
                impossible = True
            if row.get("credits") and not 0 < float(row["credits"]) <= 60:
                impossible = True
    except (ValueError, TypeError):
        impossible = True
    if impossible:
        add("IMPOSSIBLE_ACADEMIC")
    if not missing and not candidates:
        for candidate in dobs.get(str(row.get("dob")), [])[:20]:
            if str(candidate["id"]) == str(row.get("id")):
                continue
            score, matched = possible_match(row, candidate)
            if matched:
                add("POSSIBLE_DUPLICATE", "full_name", row.get("full_name"))
                candidates.append((candidate["id"], "POSSIBLE", score))
    findings.sort(key=lambda f: PRIORITY.index(f["code"]))
    for i, f in enumerate(findings):
        f["is_primary"] = i == 0
    quality = "INCOMPLETE" if missing else "FLAGGED_FOR_REVIEW" if findings else "PASSED_LOCAL_CHECKS"
    return findings, candidates, quality


def start(conn, batch):
    refs = many(
        conn,
        "SELECT id,submitted_apaar_id,submitted_enrollment_no,full_name,parent_name,dob FROM students WHERE institution_id=%s",
        (batch["institution_id"],),
    )
    claims = {
        r["apaar_id"]: str(r["id"]) for r in many(conn, "SELECT id,apaar_id FROM students WHERE apaar_id IS NOT NULL")
    }
    snapshot = dict(rows=jsonable(refs), claims=claims, rule_version=1, demo_as_of="2026-10-25")
    conn.execute(
        "UPDATE import_batches SET status='QUEUED',reference_snapshot=%s WHERE id=%s", (Jsonb(snapshot), batch["id"])
    )
    job = uuid4()
    conn.execute("INSERT INTO import_jobs(id,batch_id,status) VALUES (%s,%s,'QUEUED')", (job, batch["id"]))
    return job


def process(job_id, fail_after=None):
    try:
        with connect() as conn:
            job = one(
                conn, "SELECT * FROM import_jobs WHERE id=%s AND status='QUEUED' FOR UPDATE SKIP LOCKED", (job_id,)
            )
            if not job:
                return
            conn.execute("UPDATE import_jobs SET status='RUNNING',heartbeat_at=now() WHERE id=%s", (job_id,))
            batch = one(conn, "SELECT * FROM import_batches WHERE id=%s", (job["batch_id"],))
            read(batch["storage_key"])
            conn.execute(
                "UPDATE import_batches SET status='RUNNING',started_at=coalesce(started_at,now()) WHERE id=%s",
                (batch["id"],),
            )
        snapshot = batch["reference_snapshot"]
        indexes = make_indexes(snapshot["rows"], snapshot["claims"])
        mapping = batch["column_mapping"]["mapping"]
        with connect() as conn:
            program_rows = many(
                conn,
                "SELECT *,level||':'||branch AS code FROM programs WHERE institution_id=%s",
                (batch["institution_id"],),
            )
            programs = {p["code"]: p for p in program_rows}
            rows = many(conn, "SELECT * FROM import_rows WHERE batch_id=%s ORDER BY row_no", (batch["id"],))
        for offset in range(0, len(rows), 250):
            chunk = rows[offset : offset + 250]
            with connect() as conn:
                conn.execute("SELECT pg_advisory_xact_lock(26263,8)")
                current = one(conn, "SELECT * FROM import_jobs WHERE id=%s FOR UPDATE", (job_id,))
                for staged in chunk:
                    data = normalized(
                        staged["raw_data"], mapping, batch["column_mapping"].get("date_format", "DD/MM/YYYY")
                    )
                    sid = uuid5(batch["id"], str(staged["row_no"]))
                    data["id"] = str(sid)
                    if staged["row_no"] >= current["next_row"] and valid_id(data.get("submitted_apaar_id")):
                        claim = one(
                            conn,
                            "SELECT id FROM students WHERE apaar_id=%s AND id<>%s",
                            (data["submitted_apaar_id"], sid),
                        )
                        if claim:
                            indexes[0].setdefault(data["submitted_apaar_id"], {"id": str(claim["id"])})
                    findings, candidates, quality = evaluate(data, programs.get(data.get("program_code")), indexes)
                    if staged["row_no"] >= current["next_row"]:
                        program = programs.get(data.get("program_code"))
                        canonical_id = (
                            data.get("submitted_apaar_id")
                            if valid_id(data.get("submitted_apaar_id"))
                            and not any(f["code"] == "DUPLICATE_APAAR" for f in findings)
                            else None
                        )
                        canonical_enrollment = (
                            data.get("submitted_enrollment_no")
                            if data.get("submitted_enrollment_no") not in indexes[1]
                            else None
                        )

                        def integer(field, low, high):
                            try:
                                value = int(data[field])
                                return value if low <= value <= high else None
                            except (ValueError, KeyError, TypeError):
                                return None

                        conn.execute(
                            "INSERT INTO students(id,institution_id,program_id,apaar_id,submitted_apaar_id,enrollment_no,submitted_enrollment_no,full_name,normalized_name,transliterated_name,parent_name,dob,email,admission_year,current_year,source,data_quality_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'CSV',%s)",
                            (
                                sid,
                                batch["institution_id"],
                                program["id"] if program else None,
                                canonical_id,
                                data.get("submitted_apaar_id"),
                                canonical_enrollment,
                                data.get("submitted_enrollment_no"),
                                data.get("full_name"),
                                normalized_name(data.get("full_name")),
                                unidecode(normalized_name(data.get("full_name"))),
                                data.get("parent_name"),
                                data.get("dob"),
                                data.get("email"),
                                integer("admission_year", 1950, 2100),
                                integer("current_year", 1, 4),
                                quality,
                            ),
                        )
                        conn.execute(
                            "UPDATE import_rows SET student_id=%s,normalized_data=%s,status=%s WHERE batch_id=%s AND row_no=%s",
                            (
                                sid,
                                Jsonb(jsonable(data)),
                                "CLEAN"
                                if quality == "PASSED_LOCAL_CHECKS"
                                else "INCOMPLETE"
                                if quality == "INCOMPLETE"
                                else "FLAGGED",
                                batch["id"],
                                staged["row_no"],
                            ),
                        )
                        for f in findings:
                            conn.execute(
                                "INSERT INTO verification_checks(code,description,severity,version) VALUES (%s,%s,%s,1) ON CONFLICT DO NOTHING",
                                (f["code"], f["explanation"], f["severity"]),
                            )
                            conn.execute(
                                "INSERT INTO verification_findings(student_id,check_code,rule_version,student_version,batch_id,row_no,severity,explanation,evidence) VALUES (%s,%s,1,1,%s,%s,%s,%s,%s)",
                                (
                                    sid,
                                    f["code"],
                                    batch["id"],
                                    staged["row_no"],
                                    f["severity"],
                                    f["explanation"],
                                    Jsonb(f["evidence"]),
                                ),
                            )
                            conn.execute(
                                "INSERT INTO import_errors(batch_id,row_no,field,code,message,is_primary,evidence) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                (
                                    batch["id"],
                                    staged["row_no"],
                                    f["field"],
                                    f["code"],
                                    f["explanation"],
                                    f["is_primary"],
                                    Jsonb(f["evidence"]),
                                ),
                            )
                        if findings:
                            conn.execute(
                                "INSERT INTO review_cases(student_id,opened_reason) VALUES (%s,%s)",
                                (sid, findings[0]["code"]),
                            )
                        for target, kind, score in candidates:
                            a, b = sorted([str(sid), str(target)])
                            conn.execute(
                                "INSERT INTO duplicate_candidates(student_a,student_b,match_type,score,matched_fields) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                                (a, b, kind, round(score, 2), Jsonb(dict(source=str(sid), target=str(target)))),
                            )
                        conn.execute(
                            "INSERT INTO record_versions(student_id,version_no,snapshot,changed_fields,changed_by,reason) VALUES (%s,1,%s,%s,%s,%s)",
                            (
                                sid,
                                Jsonb(jsonable(data)),
                                Jsonb({}),
                                batch["uploader_id"],
                                "Imported synthetic source record.",
                            ),
                        )
                        append(
                            conn,
                            batch["institution_id"],
                            batch["uploader_id"],
                            "STUDENT_IMPORTED",
                            "student",
                            sid,
                            "Imported synthetic source record.",
                            dict(batch_id=str(batch["id"]), row_no=staged["row_no"], quality=quality),
                            sid,
                        )
                        if (
                            program
                            and data.get("admission_year")
                            and data.get("current_year")
                            and not any(f["code"] == "IMPOSSIBLE_ACADEMIC" for f in findings)
                            and data.get("sgpa")
                            and data.get("term_no")
                        ):
                            eno = one(
                                conn,
                                "INSERT INTO enrolments(student_id,program_id,academic_year,term_no,term_type) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                                (
                                    sid,
                                    program["id"],
                                    int(data["admission_year"]),
                                    int(data["term_no"]),
                                    program["term_type"],
                                ),
                            )["id"]
                            conn.execute(
                                "INSERT INTO academic_performance(student_id,enrolment_id,academic_year,term_no,term_type,credits,sgpa,cgpa) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                                (
                                    sid,
                                    eno,
                                    int(data["admission_year"]),
                                    int(data["term_no"]),
                                    program["term_type"],
                                    float(data.get("credits") or 22),
                                    float(data["sgpa"]),
                                    float(data["sgpa"]),
                                ),
                            )
                    # Earlier batch rows are part of the frozen reference order even on retry.
                    if data.get("submitted_apaar_id"):
                        indexes[0].setdefault(data["submitted_apaar_id"], data)
                    if data.get("submitted_enrollment_no"):
                        indexes[1].setdefault(data["submitted_enrollment_no"], data)
                    if data.get("dob"):
                        indexes[2][str(data["dob"])].append(data)
                end = chunk[-1]["row_no"]
                if end < current['next_row']:
                    continue
                counts = one(
                    conn,
                    "SELECT count(*) FILTER(WHERE status='CLEAN') AS clean,count(*) FILTER(WHERE status='FLAGGED') AS flagged,count(*) FILTER(WHERE status='INCOMPLETE') AS incomplete FROM import_rows WHERE batch_id=%s",
                    (batch["id"],),
                )
                conn.execute(
                    "UPDATE import_batches SET processed_rows=%s,clean_rows=%s,flagged_rows=%s,incomplete_rows=%s WHERE id=%s",
                    (end, counts["clean"], counts["flagged"], counts["incomplete"], batch["id"]),
                )
                conn.execute(
                    "UPDATE import_jobs SET next_row=%s,progress=%s,heartbeat_at=now() WHERE id=%s",
                    (end + 1, 100 * end / len(rows), job_id),
                )
                append(
                    conn,
                    batch["institution_id"],
                    batch["uploader_id"],
                    "IMPORT_CHUNK",
                    "import",
                    batch["id"],
                    "Committed synthetic import checkpoint.",
                    dict(processed_rows=end),
                )
                epoch(conn, batch["institution_id"])
            if fail_after and end == fail_after:
                raise RuntimeError("TEST_INTERRUPTION")
        with connect() as conn:
            conn.execute(
                "UPDATE import_jobs SET status='COMPLETED',progress=100,updated_at=now() WHERE id=%s", (job_id,)
            )
            conn.execute("UPDATE import_batches SET status='COMPLETED',finished_at=now() WHERE id=%s", (batch["id"],))
            conn.execute("SELECT refresh_demo_views()")
    except Exception:
        with connect() as conn:
            conn.execute(
                "UPDATE import_jobs SET status='FAILED',error_code='PROCESS_INTERRUPTED',error_message='Import interrupted; retry from saved checkpoint.',updated_at=now() WHERE id=%s",
                (job_id,),
            )
            conn.execute(
                "UPDATE import_batches SET status='FAILED' WHERE id=(SELECT batch_id FROM import_jobs WHERE id=%s)",
                (job_id,),
            )
        raise


def report(conn, batch_id):
    batch = one(conn, "SELECT * FROM import_batches WHERE id=%s", (batch_id,))
    buckets = many(
        conn,
        "SELECT code,count(*)::int AS count FROM import_errors WHERE batch_id=%s AND is_primary GROUP BY code ORDER BY code",
        (batch_id,),
    )
    all_count = one(conn, "SELECT count(*) AS n FROM import_errors WHERE batch_id=%s", (batch_id,))["n"]
    return dict(
        batch_id=batch_id,
        clean=batch["clean_rows"],
        flagged=batch["flagged_rows"],
        incomplete=batch["incomplete_rows"],
        affected_rows=batch["flagged_rows"] + batch["incomplete_rows"],
        primary_findings=buckets,
        all_findings=all_count,
        secondary_findings=all_count - sum(b["count"] for b in buckets),
        processed_rows=batch["processed_rows"],
        total_rows=batch["total_rows"],
        status=batch["status"],
    )
