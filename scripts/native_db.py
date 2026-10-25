"""Start an isolated, loopback-only PostgreSQL cluster inside this project."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from demo import env


def run():
    values = env()
    base = ROOT / ".local"
    binaries = base / "pgsql/bin"
    data = base / "pgdata"
    process_env = {**os.environ, "PGPASSWORD": values["POSTGRES_PASSWORD"]}
    if not data.exists():
        password = base / "pg-init-secret"
        password.write_text(values["POSTGRES_PASSWORD"], encoding="utf-8")
        try:
            subprocess.run(
                [
                    str(binaries / "initdb.exe"),
                    "-D",
                    str(data),
                    "-U",
                    "shiksham_owner",
                    "--pwfile",
                    str(password),
                    "-A",
                    "scram-sha-256",
                    "--encoding=UTF8",
                    "--locale=C",
                ],
                check=True,
            )
        finally:
            password.unlink(missing_ok=True)
        with (data / "postgresql.conf").open("a") as f:
            f.write("\nlisten_addresses='127.0.0.1'\nport=55432\nshared_buffers='256MB'\nmax_connections=40\n")
    status = subprocess.run([str(binaries / "pg_ctl.exe"), "-D", str(data), "status"], capture_output=True)
    if status.returncode:
        subprocess.run(
            [str(binaries / "pg_ctl.exe"), "-D", str(data), "-l", str(base / "postgres.log"), "start"], check=True
        )
    result = subprocess.run(
        [
            str(binaries / "psql.exe"),
            "-h",
            "127.0.0.1",
            "-p",
            "55432",
            "-U",
            "shiksham_owner",
            "-d",
            "postgres",
            "-Atc",
            "SELECT 1 FROM pg_database WHERE datname='shiksham'",
        ],
        env=process_env,
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip() != "1":
        subprocess.run(
            [str(binaries / "createdb.exe"), "-h", "127.0.0.1", "-p", "55432", "-U", "shiksham_owner", "shiksham"],
            env=process_env,
            check=True,
        )
    print("Native PostgreSQL available at 127.0.0.1:55432; database shiksham.")


if __name__ == "__main__":
    run()
