"""Fixed SQL for analytics transactions."""

from app.db.session import one, many


def oversight_institutions(conn, params=()):
    return many(
        conn,
        "SELECT id,name,state FROM institutions WHERE (%s::text IS NULL OR state=%s) AND (%s::uuid IS NULL OR id=%s) ORDER BY name LIMIT %s OFFSET %s",
        params,
    )


def oversight_institutions_2(conn, params=()):
    return one(
        conn,
        "SELECT count(*) AS n FROM institutions WHERE (%s::text IS NULL OR state=%s) AND (%s::uuid IS NULL OR id=%s)",
        params,
    )


def oversight_data_quality_snapshots(conn, params=()):
    return many(
        conn,
        "SELECT snapshot_date AS date,round(100.0*sum(s.clean)/nullif(sum(s.total),0),2) AS clean_percent FROM data_quality_snapshots s JOIN institutions i ON i.id=s.institution_id WHERE (%s::text IS NULL OR i.state=%s) AND (%s::uuid IS NULL OR i.id=%s) GROUP BY snapshot_date ORDER BY snapshot_date",
        params,
    )


def analytics_data_institutions(conn, params=()):
    return one(conn, "SELECT state FROM institutions WHERE id=%s", params)


def analytics_data_analytics_refresh_state(conn, params=()):
    return one(conn, "SELECT * FROM analytics_refresh_state WHERE view_name=%s", params)


def analytics_data_institution_epochs(conn, params=()):
    return one(conn, "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs", params)


def analytics_data_data_quality_snapshots(conn, params=()):
    return many(
        conn,
        "SELECT snapshot_date AS date,round(100.0*sum(d.clean)/nullif(sum(d.total),0),2) AS clean_percent FROM data_quality_snapshots d JOIN institutions i ON i.id=d.institution_id WHERE (%s::uuid[] IS NULL OR d.institution_id=ANY(%s::uuid[])) AND (%s::text IS NULL OR i.state=%s) GROUP BY snapshot_date ORDER BY snapshot_date",
        params,
    )


def refresh_query(conn, params=()):
    return conn.execute("SELECT refresh_demo_views()", params)


def refresh_status_analytics_refresh_state(conn, params=()):
    return many(conn, "SELECT view_name AS name,status,refreshed_at,source_epoch FROM analytics_refresh_state", params)


def refresh_status_institution_epochs(conn, params=()):
    return one(conn, "SELECT coalesce(sum(data_epoch),0) AS e FROM institution_epochs", params)
