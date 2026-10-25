"""Analytics HTTP operations."""

from app.core.http import listing, pagination
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID
from fastapi import Depends, BackgroundTasks
from app.db.session import connect, one, many
from app.core.errors import fail
from app.core.security import authenticated, allow, institution_scope
from app.core.rate_limit import limit
from app.modules.students.service import dashboard
from fastapi import APIRouter

router = APIRouter(tags=["analytics"])


@router.get("/oversight")
def oversight(
    state: str | None = None,
    institution_id: UUID | None = None,
    program_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    user=Depends(authenticated),
):
    allow(user, "ADMIN")
    offset = pagination(page, page_size)
    with connect() as conn:
        from app.modules.students.aggregates import program_dashboard

        program_data = program_dashboard(conn, program_id, institution_id) if program_id else None
        if program_data:
            institution_id = program_data["institution_id"]
        insts = many(
            conn,
            "SELECT id,name,state FROM institutions WHERE (%s::text IS NULL OR state=%s) AND (%s::uuid IS NULL OR id=%s) ORDER BY name LIMIT %s OFFSET %s",
            (state, state, institution_id, institution_id, page_size, offset),
        )
        rows = []
        for inst in insts:
            data = program_data or dashboard(conn, inst["id"])
            rows.append(
                dict(
                    institution_id=inst["id"],
                    institution_name=inst["name"],
                    state=inst["state"],
                    total=data["total"],
                    submission_percent=data["submission_percent"],
                    missing_records=data["missing_records"],
                    unresolved_discrepancies=data["flagged"],
                    pending_reviews=data["pending_reviews"],
                )
            )
        total = one(
            conn,
            "SELECT count(*) AS n FROM institutions WHERE (%s::text IS NULL OR state=%s) AND (%s::uuid IS NULL OR id=%s)",
            (state, state, institution_id, institution_id),
        )["n"]
        trend = many(
            conn,
            "SELECT snapshot_date AS date,round(100.0*sum(s.clean)/nullif(sum(s.total),0),2) AS clean_percent FROM data_quality_snapshots s JOIN institutions i ON i.id=s.institution_id WHERE (%s::text IS NULL OR i.state=%s) AND (%s::uuid IS NULL OR i.id=%s) GROUP BY snapshot_date ORDER BY snapshot_date",
            (state, state, institution_id, institution_id),
        )
        return listing(rows, total=total, page=page, page_size=page_size, trend=trend)


def analytics_data(kind, user, institution_id, program_id, year, state):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    ids = institution_scope(user, institution_id, admin=True)
    table = {
        "admissions": "mv_admissions",
        "placements": "mv_placements",
        "performance": "mv_performance",
        "data-quality": "mv_data_quality",
    }[kind]
    start = perf_counter()
    with connect() as conn:
        if kind == "data-quality" and year:
            fail(
                "INVALID_FILTER_COMBINATION",
                422,
                "Year-scoped expected-record denominators are not configured for data quality.",
            )
        if kind == "data-quality" and program_id:
            from app.modules.students.aggregates import program_dashboard

            result = program_dashboard(conn, program_id, institution_id)
            institution_scope(user, result["institution_id"], admin=True)
            state_row = one(conn, "SELECT state FROM institutions WHERE id=%s", (result["institution_id"],))
            if state and state_row["state"] != state:
                fail("INVALID_FILTER_COMBINATION")
            return dict(
                items=[result],
                trend=[],
                took_ms=round((perf_counter() - start) * 1000, 3),
                data_as_of=datetime.now(timezone.utc),
                refreshing=False,
                stale=False,
            )
        pred = "(%s::uuid[] IS NULL OR v.institution_id=ANY(%s::uuid[])) AND (%s::text IS NULL OR i.state=%s)"
        params: tuple = (ids, ids, state, state)
        if kind != "data-quality":
            pred += " AND (%s::uuid IS NULL OR v.program_id=%s) AND (%s::int IS NULL OR v.year=%s)"
            params += (program_id, program_id, year, year)
        rows = many(
            conn, f"SELECT v.* FROM {table} v JOIN institutions i ON i.id=v.institution_id WHERE " + pred, params
        )
        refresh = one(conn, "SELECT * FROM analytics_refresh_state WHERE view_name=%s", (table,))
        current = one(conn, "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs")["e"]
        trend = []
        if kind == "data-quality":
            trend = many(
                conn,
                "SELECT snapshot_date AS date,round(100.0*sum(d.clean)/nullif(sum(d.total),0),2) AS clean_percent FROM data_quality_snapshots d JOIN institutions i ON i.id=d.institution_id WHERE (%s::uuid[] IS NULL OR d.institution_id=ANY(%s::uuid[])) AND (%s::text IS NULL OR i.state=%s) GROUP BY snapshot_date ORDER BY snapshot_date",
                (ids, ids, state, state),
            )
        return dict(
            items=rows,
            trend=trend,
            took_ms=round((perf_counter() - start) * 1000, 3),
            data_as_of=refresh["refreshed_at"],
            refreshing=refresh["status"] == "RUNNING",
            stale=refresh["source_epoch"] != current,
        )


for kind in ["admissions", "placements", "performance", "data-quality"]:

    def make_endpoint(selected):
        def endpoint(
            institution_id: UUID | None = None,
            program_id: UUID | None = None,
            year: int | None = None,
            state: str | None = None,
            user=Depends(authenticated),
        ):
            return analytics_data(selected, user, institution_id, program_id, year, state)

        endpoint.__name__ = "analytics_" + selected.replace("-", "_")
        return endpoint

    router.add_api_route("/analytics/" + kind, make_endpoint(kind), methods=["GET"])


@router.post("/analytics/refresh", status_code=202)
def refresh_analytics(tasks: BackgroundTasks, user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    limit(("refresh", str(user["id"])), 1, 10)

    def refresh():
        with connect() as conn:
            conn.execute("SELECT refresh_demo_views()")

    tasks.add_task(refresh)
    return dict(status="QUEUED", poll_url="/api/v1/analytics/refresh-status")


@router.get("/analytics/refresh-status")
def refresh_status(user=Depends(authenticated)):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    with connect() as conn:
        views = many(conn, "SELECT view_name AS name,status,refreshed_at,source_epoch FROM analytics_refresh_state")
        current = one(conn, "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs")["e"]
        return dict(
            status="READY" if all(v["status"] == "READY" for v in views) else "RUNNING",
            views=views,
            stale=any(v["source_epoch"] != current for v in views),
        )
