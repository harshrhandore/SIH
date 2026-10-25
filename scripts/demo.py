"""Local environment management; secrets are printed only on explicit request."""

import argparse
import secrets
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def env():
    return dict(
        line.split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )


def init_env(native=False):
    target = ROOT / ".env"
    if target.exists():
        print("Environment already exists; left unchanged.")
        return
    values = dict(line.split("=", 1) for line in (ROOT / ".env.example").read_text().splitlines() if "=" in line)
    for key in [
        "POSTGRES_PASSWORD",
        "RUNTIME_DB_PASSWORD",
        "JWT_SECRET",
        "MASK_SECRET",
        "GRANT_SECRET",
        "DEMO_PASSWORD",
    ]:
        values[key] = secrets.token_urlsafe(36)
    host = "127.0.0.1:55432" if native else "db:5432"
    values["DATABASE_OWNER_URL"] = (
        f"postgresql://shiksham_owner:{quote(values['POSTGRES_PASSWORD'], safe='')}@{host}/shiksham"
    )
    values["DATABASE_URL"] = (
        f"postgresql://shiksham_runtime:{quote(values['RUNTIME_DB_PASSWORD'], safe='')}@{host}/shiksham"
    )
    target.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    print("Created .env with generated secrets. Use show-demo-password locally to view the demo password.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-env", "show-demo-password"])
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    if args.command == "init-env":
        init_env(args.native)
    else:
        print(env()["DEMO_PASSWORD"])
