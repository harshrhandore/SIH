from app.modules.imports import repository
from app.modules.verification.matching import make_indexes as make_indexes
from app.modules.verification.rules import evaluate as evaluate
from app.modules.imports.mapping import ALIASES as ALIASES, MANDATORY as MANDATORY, normalized as normalized
from uuid import uuid5
from unidecode import unidecode
from psycopg.types.json import Jsonb
from app.core.algorithms import valid_id, normalized_name
from app.core.audit import append
from app.core.files import read
from app.db.session import connect
from app.modules.students.service import jsonable, epoch
import asyncio
import psycopg
import logging
from concurrent.futures import ThreadPoolExecutor
from app.settings import settings

logger = logging.getLogger("shiksham.import_recovery")


def process(job_id, fail_after=None):
    # A session lock protects the gaps between checkpoint transactions and
    # lets recovery distinguish an alive worker from an interrupted process.
    with psycopg.connect(settings.database_url, autocommit=True) as lock:
        slot = lock.execute("SELECT pg_try_advisory_lock(26263,7)").fetchone()
        if not slot or not slot[0]:
            return
        try:
            acquired = lock.execute(
                "SELECT pg_try_advisory_lock(hashtextextended(%s,26263))", (str(job_id),)
            ).fetchone()
            if not acquired or not acquired[0]:
                return
            return _process(job_id, fail_after)
        finally:
            lock.execute("SELECT pg_advisory_unlock(hashtextextended(%s,26263))", (str(job_id),))
            lock.execute("SELECT pg_advisory_unlock(26263,7)")


async def schedule(stop):
    pending = set()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="import-recovery")
    failures = 0

    def scan():
        with connect() as conn:
            return repository.recover_and_list_queued(conn)

    try:
        while not stop.is_set():
            try:
                rows = await asyncio.to_thread(scan)
                failures = 0
            except Exception as error:
                failures = min(failures + 1, 4)
                logger.warning("Import recovery scan unavailable (%s); retry scheduled.", type(error).__name__)
                rows = []
            for row in rows:
                key = row["id"]
                if key not in pending:
                    pending.add(key)
                    future = executor.submit(process, key)

                    def finished(done, job=key):
                        pending.discard(job)
                        if not done.cancelled() and done.exception():
                            logger.warning(
                                "Import worker stopped; checkpoint retained (%s).", type(done.exception()).__name__
                            )

                    future.add_done_callback(finished)
            try:
                await asyncio.wait_for(stop.wait(), timeout=min(60, 5 * 2**failures))
            except TimeoutError:
                pass
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _process(job_id, fail_after=None):
    try:
        with connect() as conn:
            job = repository.process_import_jobs(conn, (job_id,))
            if not job:
                return
            repository.process_import_jobs_2(conn, (job_id,))
            batch = repository.process_import_batches(conn, (job["batch_id"],))
            read(batch["storage_key"])
            repository.process_import_batches_2(conn, (batch["id"],))
        snapshot = batch["reference_snapshot"]
        indexes = make_indexes(snapshot["rows"], snapshot["claims"])
        mapping = batch["column_mapping"]["mapping"]
        with connect() as conn:
            program_rows = repository.process_programs(conn, (batch["institution_id"],))
            programs = {p["code"]: p for p in program_rows}
            rows = repository.process_import_rows(conn, (batch["id"],))
        for offset in range(0, len(rows), 250):
            chunk = rows[offset : offset + 250]
            with connect() as conn:
                repository.process_query(conn, ())
                current = repository.process_import_jobs_3(conn, (job_id,))
                for staged in chunk:
                    data = normalized(
                        staged["raw_data"], mapping, batch["column_mapping"].get("date_format", "DD/MM/YYYY")
                    )
                    sid = uuid5(batch["id"], str(staged["row_no"]))
                    data["id"] = str(sid)
                    if staged["row_no"] >= current["next_row"] and valid_id(data.get("submitted_apaar_id")):
                        claim = repository.process_students(conn, (data["submitted_apaar_id"], sid))
                        if claim:
                            indexes[0].setdefault(data["submitted_apaar_id"], {"id": str(claim["id"])})
                    if staged["row_no"] >= current["next_row"] and data.get("submitted_enrollment_no"):
                        live = repository.process_students_2(
                            conn, (batch["institution_id"], data["submitted_enrollment_no"], sid)
                        )
                        if live:
                            indexes[1].setdefault(data["submitted_enrollment_no"], live)
                    findings, candidates, quality = evaluate(data, programs.get(data.get("program_code")), indexes)
                    if staged["row_no"] >= current["next_row"]:
                        program = programs.get(data.get("program_code"))
                        canonical_id = (
                            data.get("submitted_apaar_id")
                            if valid_id(data.get("submitted_apaar_id"))
                            and (not any((f["code"] == "DUPLICATE_APAAR" for f in findings)))
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

                        repository.process_students_3(
                            conn,
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
                        repository.process_import_rows_2(
                            conn,
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
                            repository.process_verification_checks(conn, (f["code"], f["explanation"], f["severity"]))
                            repository.process_verification_findings(
                                conn,
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
                            repository.process_import_errors(
                                conn,
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
                            repository.process_review_cases(conn, (sid, findings[0]["code"]))
                        for target, kind, score in candidates:
                            a, b = sorted([str(sid), str(target)])
                            repository.process_duplicate_candidates(
                                conn, (a, b, kind, round(score, 2), Jsonb(dict(source=str(sid), target=str(target))))
                            )
                        repository.process_record_versions(
                            conn,
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
                            and (not any((f["code"] == "IMPOSSIBLE_ACADEMIC" for f in findings)))
                            and data.get("sgpa")
                            and data.get("term_no")
                        ):
                            eno = repository.process_enrolments(
                                conn,
                                (
                                    sid,
                                    program["id"],
                                    int(data["admission_year"]),
                                    int(data["term_no"]),
                                    program["term_type"],
                                ),
                            )["id"]
                            repository.process_academic_performance(
                                conn,
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
                    if data.get("submitted_apaar_id"):
                        indexes[0].setdefault(data["submitted_apaar_id"], data)
                    if data.get("submitted_enrollment_no"):
                        indexes[1].setdefault(data["submitted_enrollment_no"], data)
                    if data.get("dob"):
                        indexes[2][str(data["dob"])].append(data)
                end = chunk[-1]["row_no"]
                if end < current["next_row"]:
                    continue
                counts = repository.process_import_rows_3(conn, (batch["id"],))
                repository.process_import_batches_3(
                    conn, (end, counts["clean"], counts["flagged"], counts["incomplete"], batch["id"])
                )
                repository.process_import_jobs_4(conn, (end + 1, 100 * end / len(rows), job_id))
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
            repository.process_import_jobs_5(conn, (job_id,))
            repository.process_import_batches_4(conn, (batch["id"],))
            repository.process_query_2(conn, ())
    except Exception:
        with connect() as conn:
            repository.process_import_jobs_6(conn, (job_id,))
            repository.process_import_batches_5(conn, (job_id,))
        raise
