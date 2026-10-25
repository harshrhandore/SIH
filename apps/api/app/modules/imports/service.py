from app.modules.verification.matching import make_indexes as make_indexes
from app.modules.verification.rules import evaluate as evaluate
from app.modules.imports.mapping import ALIASES as ALIASES, MANDATORY as MANDATORY, normalized as normalized
from datetime import datetime, date
from io import BytesIO, StringIO
import csv
from uuid import uuid4, uuid5
from unidecode import unidecode
import zipfile
from openpyxl import load_workbook
from psycopg.types.json import Jsonb
from app.core.algorithms import valid_id, normalized_name
from app.core.audit import append
from app.core.errors import fail
from app.core.files import store, read
from app.db.session import connect, one, many
from app.modules.students.service import jsonable, epoch


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
                if sheet.max_column and sheet.max_column > 100:
                    fail("INVALID_HEADERS")
                if sheet.max_row and sheet.max_row > 1001:
                    fail("TOO_MANY_ROWS")
                rows = list(sheet.iter_rows())
                if any(any(c.value is not None for c in row) for row in rows):
                    nonempty.append(rows)
            if len(nonempty) != 1:
                fail("WORKSHEET_SELECTION_REQUIRED")
            cells = nonempty[0]
            if any(c.data_type == "f" for row in cells for c in row):
                fail("XLSX_FORMULA_NOT_SUPPORTED")
            headers = [str(c.value or "") for c in cells[0]]
            rows = [
                {
                    h: (
                        c.value.date().isoformat()
                        if isinstance(c.value, datetime)
                        else c.value.isoformat()
                        if isinstance(c.value, date)
                        else str(c.value)
                        if c.value is not None
                        else ""
                    )
                    for h, c in zip(headers, row)
                }
                for row in cells[1:]
            ]
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
                    if staged["row_no"] >= current["next_row"] and data.get("submitted_enrollment_no"):
                        live = one(
                            conn,
                            "SELECT id,submitted_enrollment_no,full_name,parent_name,dob FROM students WHERE institution_id=%s AND enrollment_no=%s AND id<>%s",
                            (batch["institution_id"], data["submitted_enrollment_no"], sid),
                        )
                        if live:
                            indexes[1].setdefault(data["submitted_enrollment_no"], live)
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
                if end < current["next_row"]:
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
