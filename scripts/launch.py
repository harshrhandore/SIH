import argparse, os, subprocess, sys
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("service", choices=["api", "web"])
args = p.parse_args()
values = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}
if args.service == "api":
    env = {**os.environ, **values, "PYTHONPATH": os.pathsep.join([str(ROOT / "apps/api"), str(ROOT)])}
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--no-access-log",
    ]
else:
    env = {**os.environ, **{k: values[k] for k in ["WEB_ORIGIN", "API_INTERNAL_ORIGIN", "COOKIE_SECURE"]}}
    command = ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"]
raise SystemExit(subprocess.call(command, cwd=ROOT, env=env))
