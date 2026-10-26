from app.modules.analytics import repository
from app.core.http import listing, pagination
from datetime import datetime, timezone
from time import perf_counter
from uuid import UUID
from fastapi import BackgroundTasks
from app.db.session import connect, many
from app.core.errors import fail
from app.core.security import allow, institution_scope
from app.core.rate_limit import limit
from app.modules.students.service import dashboard


def oversight(
    state: str | None = None,
    institution_id: UUID | None = None,
    program_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
    user=None,
):
    allow(user, "ADMIN")
    offset = pagination(page, page_size)
    with connect() as conn:
        from app.modules.students.aggregates import program_dashboard

        program_data = program_dashboard(conn, program_id, institution_id) if program_id else None
        if program_data:
            institution_id = program_data["institution_id"]
        insts = repository.oversight_institutions(
            conn, (state, state, institution_id, institution_id, page_size, offset)
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
        total = repository.oversight_institutions_2(conn, (state, state, institution_id, institution_id))["n"]
        trend = repository.oversight_data_quality_snapshots(conn, (state, state, institution_id, institution_id))
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
            state_row = repository.analytics_data_institutions(conn, (result["institution_id"],))
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
        refresh = repository.analytics_data_analytics_refresh_state(conn, (table,))
        current = repository.analytics_data_institution_epochs(conn, ())["e"]
        trend = []
        if kind == "data-quality":
            trend = repository.analytics_data_data_quality_snapshots(conn, (ids, ids, state, state))
        return dict(
            items=rows,
            trend=trend,
            took_ms=round((perf_counter() - start) * 1000, 3),
            data_as_of=refresh["refreshed_at"],
            refreshing=refresh["status"] == "RUNNING",
            stale=refresh["source_epoch"] != current,
        )


def refresh_analytics(tasks: BackgroundTasks, user=None):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    limit(("refresh", str(user["id"])), 1, 10)

    from app.modules.analytics.refresh import run

    tasks.add_task(run)
    return dict(status="QUEUED", poll_url="/api/v1/analytics/refresh-status")


def refresh_status(user=None):
    allow(user, "OPERATOR", "OFFICER", "ADMIN")
    with connect() as conn:
        views = repository.refresh_status_analytics_refresh_state(conn, ())
        current = repository.refresh_status_institution_epochs(conn, ())["e"]
        return dict(
            status="READY" if all((v["status"] == "READY" for v in views)) else "RUNNING",
            views=views,
            stale=any((v["source_epoch"] != current for v in views)),
        )
