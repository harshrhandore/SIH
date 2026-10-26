from app.modules.verification import repository
from app.core.audit import append
from app.modules.students.service import epoch
from psycopg.types.json import Jsonb
from datetime import datetime, timezone


def verify_mock(conn, student, user, note):
    from app.integrations.mock_apaar import MockApaarAdapter

    external_result = MockApaarAdapter().verify(student)
    status = external_result["status"]
    evidence = dict(
        label=external_result["label"],
        reasons=external_result["reasons"],
        reference=external_result["reference"],
    )
    repository.work_external_verifications(conn, (student["id"], user["id"], status, Jsonb(evidence)))
    repository.work_students(conn, (status, student["id"]))
    append(
        conn,
        student["institution_id"],
        user["id"],
        "MOCK_EXTERNAL_CHECK",
        "student",
        student["id"],
        note,
        dict(status=status, official=False),
        student["id"],
    )
    epoch(conn, student["institution_id"])
    return dict(
        adapter="MockApaarAdapter",
        status=status,
        official=False,
        checked_at=str(datetime.now(timezone.utc)),
        **evidence,
    )
