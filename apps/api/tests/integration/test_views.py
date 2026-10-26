from uuid import uuid4
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.settings import ROOT
from app.db.session import connect, one
from db.seed.fixtures import uid

client = TestClient(app)


def login(email):
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]}
    )
    assert r.status_code == 200, r.text
    value = r.json()
    return (
        value,
        {
            "Authorization": "Bearer " + value["access_token"],
            "X-CSRF-Token": value["csrf_token"],
            "Idempotency-Key": str(uuid4()),
        },
    )


def test_program_oversight_denominator_and_state_trend():
    _, admin = login("admin@example.test")
    program = str(uid("program", "0:BTECH:CSE"))
    institution = str(uid("institution", 0))
    response = client.get(
        "/api/v1/oversight", params={"institution_id": institution, "program_id": program}, headers=admin
    )
    assert response.status_code == 200, response.text
    result = response.json()
    with connect() as conn:
        actual = one(conn, "SELECT count(*) AS n FROM students WHERE program_id=%s", (program,))["n"]
        expected = one(
            conn, "SELECT expected_records AS n FROM program_expected_records WHERE program_id=%s", (program,)
        )["n"]
    assert result["total"] == 1 and result["items"][0]["total"] == actual
    assert result["items"][0]["missing_records"] == max(0, expected - actual)
    wrong = client.get(
        "/api/v1/oversight", params={"institution_id": str(uid("institution", 1)), "program_id": program}, headers=admin
    )
    assert wrong.status_code == 422
    quality = client.get("/api/v1/analytics/data-quality?state=Maharashtra", headers=admin)
    assert quality.status_code == 200, quality.text
    # Compare real scoped snapshot numerators/denominators. Browser import
    # rehearsals legitimately create historic non-100% points in institution B.
    with connect() as conn:
        states = conn.execute("SELECT id FROM institutions WHERE state='Maharashtra'").fetchall()
        snapshots = conn.execute("SELECT snapshot_date,clean,total FROM data_quality_snapshots WHERE institution_id=ANY(%s::uuid[])", ([row["id"] for row in states],)).fetchall()
    totals = defaultdict(lambda: [0, 0])
    for snapshot in snapshots:
        totals[str(snapshot["snapshot_date"])][0] += snapshot["clean"]
        totals[str(snapshot["snapshot_date"])][1] += snapshot["total"]
    expected_trend = [{"date": stamp, "clean_percent": float((Decimal(100) * clean / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if total else None} for stamp, (clean,total) in sorted(totals.items())]
    assert expected_trend and quality.json()["trend"] == expected_trend


def test_multiple_offers_count_one_student():
    with connect() as conn:
        conn.execute("BEGIN")
        student = uid("student", 1)
        program = uid("program", "0:BTECH:CSE")
        for suffix, amount in [("A", 12), ("B", 13)]:
            conn.execute(
                "INSERT INTO placements(student_id,company,role,package_lpa,placement_year,offer_status) VALUES (%s,%s,'Synthetic regression role',%s,2026,'OFFERED')",
                (student, "Synthetic regression " + suffix, amount),
            )
        conn.execute("SELECT refresh_demo_views()")
        row = one(
            conn,
            "SELECT * FROM mv_placements WHERE institution_id=%s AND program_id=%s AND year=2026",
            (uid("institution", 0), program),
        )
        distinct = one(
            conn,
            "SELECT count(DISTINCT s.id)::int AS n FROM students s JOIN programs p ON p.id=s.program_id JOIN placements pl ON pl.student_id=s.id AND pl.placement_year=s.admission_year+p.duration_years AND pl.offer_status IN ('OFFERED','ACCEPTED') WHERE s.program_id=%s AND s.current_year=p.duration_years AND s.status<>'WITHDRAWN' AND s.admission_year+p.duration_years=2026",
            (program,),
        )["n"]
        assert row["placed_students"] == distinct <= row["eligible_students"]
        conn.rollback()
