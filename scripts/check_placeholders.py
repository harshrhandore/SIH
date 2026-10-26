"""Check registered external placeholders and scan project sources for unfinished markers/secrets."""

import json, re, subprocess, sys
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def tracked():
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True
    )
    return [ROOT / p for p in sorted(set(output.splitlines())) if (ROOT / p).is_file()]


def check():
    errors = []
    register = ROOT / "docs/owner-register.json"
    rows = json.loads(register.read_text()) if register.exists() else []
    registered = {r["variable"] for r in rows if r["id"].startswith("P")}
    found = set()
    marker = "<<" + "FILL_ME:"
    forbidden = ["GENERATE" + "_WITH_INIT", "TO" + "DO", "FIX" + "ME", "X" + "XX", "lorem" + " ipsum", "change" + "me"]
    generated = {
        "POSTGRES_PASSWORD",
        "RUNTIME_DB_PASSWORD",
        "DATABASE_URL",
        "DATABASE_OWNER_URL",
        "JWT_SECRET",
        "MASK_SECRET",
        "GRANT_SECRET",
        "DEMO_PASSWORD",
    }
    secrets = [v for k, v in dotenv_values(ROOT / ".env").items() if k in generated and v and len(v) >= 16]
    for path in tracked():
        relative = path.relative_to(ROOT).as_posix()
        ui_source = relative.startswith("apps/web/src/") and path.suffix in {".ts", ".tsx", ".css"}
        if path.suffix.lower() in {".pdf", ".png", ".xlsx", ".woff2", ".woff", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, ValueError):
            if ui_source:
                errors.append(f"{relative}: UI source is not valid UTF-8")
            continue
        if ui_source and any(bad in text for bad in ["\u00c2\u00b7", "\u00e2\u20ac", "\u00c3\u201a", "\ufffd"]):
            errors.append(f"{relative}: corrupted UI text encoding")
        tokens = set(re.findall(re.escape(marker) + r"([A-Z0-9_]+)>>", text))
        found |= tokens
        if relative in {".env.example", ".env.production.example"}:
            for line in text.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    if not value and key not in generated:
                        found.add(key)
        elif relative not in {"scripts/check_placeholders.py"}:
            for word in forbidden:
                if word.casefold() in text.casefold():
                    errors.append(f"{relative}: unfinished marker {word}")
            if tokens:
                errors.append(f"{relative}: external placeholder outside registered example")
        if any(secret in text for secret in secrets):
            errors.append(f"{relative}: contains a generated local secret")
    if found != registered:
        errors.append(
            f"Placeholder registration differs: missing {sorted(found - registered)}, stale {sorted(registered - found)}"
        )
    decisions = (ROOT / "OWNER_DECISIONS.md").read_text(encoding="utf-8-sig")
    for row in rows:
        if row["id"] not in decisions:
            errors.append("Owner row missing: " + row["id"])
        for key in ["id", "priority", "what", "where", "why", "fallback", "resolve", "verify", "status"]:
            if not row.get(key):
                errors.append(row["id"] + ": empty " + key)
    for p in ["docs/conformance-matrix.md", "docs/verification-report.md"]:
        content = (ROOT / p).read_text(encoding="utf-8-sig")
        for line in content.splitlines():
            if "UNVERIFIED-" in line or "BLOCKED" in line:
                ids = re.findall(r"\bV\d+\b", line)
                if not ids or any(i not in {r["id"] for r in rows if r["id"].startswith("V")} for i in ids):
                    errors.append(p + ": unregistered verification gap")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Placeholder and secret scan passed; {len(found)} registered external variables, {len(rows)} owner rows.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
