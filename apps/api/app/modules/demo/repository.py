"""Fixed SQL statements for demo transactions."""

from app.db.session import one, many


def demo_config_students(conn, params=()):
    return one(conn, "SELECT count(*) AS n FROM students", params)


def performance_pg_indexes(conn, params=()):
    return many(
        conn, "SELECT indexname AS name,indexdef AS definition FROM pg_indexes WHERE tablename='students'", params
    )


def work_query(conn, params=()):
    return conn.execute("SELECT pg_advisory_xact_lock(26263,77)", params)


def work_benchmark_runs(conn, params=()):
    return one(
        conn, "SELECT 1 FROM benchmark_runs WHERE status='RUNNING' AND created_at>now()-interval '5 minutes'", params
    )


def work_benchmark_runs_2(conn, params=()):
    return conn.execute("INSERT INTO benchmark_runs(id,requested_by,status) VALUES (%s,%s,'RUNNING')", params)


def execute_benchmark_benchmark_runs(conn, params=()):
    return conn.execute("UPDATE benchmark_runs SET status='COMPLETED',result=%s,finished_at=now() WHERE id=%s", params)


def execute_benchmark_benchmark_runs_2(conn, params=()):
    return conn.execute("UPDATE benchmark_runs SET status='FAILED',result=%s,finished_at=now() WHERE id=%s", params)


def benchmark_result_benchmark_runs(conn, params=()):
    return one(
        conn,
        "SELECT id AS run_id,status,result,created_at,finished_at,requested_by FROM benchmark_runs WHERE id=%s",
        params,
    )
