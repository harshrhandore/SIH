from uuid import uuid4
import hashlib
import psycopg
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import connect, one
from app.settings import ROOT, settings
from app.core.files import contained, root_path
from app.modules.imports import repository, service
from db.seed.fixtures import uid


def test_retry_replays_once_and_recovers_orphaned_jobs(monkeypatch):
    client = TestClient(app)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "operator.b@example.test", "password": dotenv_values(ROOT / ".env")["DEMO_PASSWORD"]},
    )
    assert login.status_code == 200
    headers = {
        "Authorization": "Bearer " + login.json()["access_token"],
        "Idempotency-Key": str(uuid4()),
        "X-CSRF-Token": login.json()["csrf_token"],
    }
    batch, job = uuid4(), uuid4()
    key = f"test-retry/{batch}.csv"
    path = contained(root_path(settings.storage_root), key)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"Synthetic regression source\n"
    path.write_bytes(data)
    queued = []
    monkeypatch.setattr(service, "process", lambda value: queued.append(str(value)))
    guard = psycopg.connect(settings.database_url, autocommit=True)
    guard.execute("SELECT pg_advisory_lock(hashtextextended(%s,26263))", (str(job),))
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO import_batches(id,institution_id,uploader_id,filename,storage_key,file_sha256,status,total_rows,processed_rows) VALUES (%s,%s,%s,'synthetic-retry.csv',%s,%s,'FAILED',1000,500)",
                (batch, uid("institution", 1), uid("user", "operator_b"), key, hashlib.sha256(data).hexdigest()),
            )
            conn.execute(
                "INSERT INTO import_jobs(id,batch_id,status,next_row) VALUES (%s,%s,'FAILED',501)", (job, batch)
            )
        url = f"/api/v1/import-jobs/{job}/retry"
        body = {"reason": "Retry after a synthetic process interruption."}
        missing = client.post(url, headers={k: v for k, v in headers.items() if k != "Idempotency-Key"}, json=body)
        assert missing.status_code == 422
        response = client.post(url, headers=headers, json=body)
        assert response.status_code == 202, response.text
        assert response.json()["resume_from_row"] == 501 and response.json()["retry_count"] == 1
        replay = client.post(url, headers=headers, json=body)
        assert replay.status_code == 202 and replay.json() == response.json()
        assert queued == [str(job)]
        with connect() as conn:
            assert one(conn, "SELECT retry_count FROM import_jobs WHERE id=%s", (job,))["retry_count"] == 1
            assert job in {row["id"] for row in repository.recover_and_list_queued(conn)}
            conn.execute(
                "UPDATE import_jobs SET status='RUNNING',heartbeat_at=now()-interval '61 seconds' WHERE id=%s", (job,)
            )
            conn.execute("UPDATE import_batches SET status='RUNNING' WHERE id=%s", (batch,))
        guard.close()
        with psycopg.connect(settings.database_url, autocommit=True) as lock:
            lock.execute("SELECT pg_advisory_lock(hashtextextended(%s,26263))", (str(job),))
            with connect() as conn:
                repository.recover_and_list_queued(conn)
                assert one(conn, "SELECT status FROM import_jobs WHERE id=%s", (job,))["status"] == "RUNNING"
        with connect() as conn:
            repository.recover_and_list_queued(conn)
            assert one(conn, "SELECT status FROM import_jobs WHERE id=%s", (job,))["status"] == "FAILED"
            assert one(conn, "SELECT status FROM import_batches WHERE id=%s", (batch,))["status"] == "FAILED"
    finally:
        guard.close()
        with connect() as conn:
            conn.execute("DELETE FROM import_jobs WHERE id=%s", (job,))
            conn.execute("DELETE FROM import_batches WHERE id=%s", (batch,))
        path.unlink(missing_ok=True)
