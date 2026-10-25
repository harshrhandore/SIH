"""Apply the audited lock helper to this development database after initial migration."""

from app.cli import owner_url
from app.db.session import connect
from app.settings import ROOT

with connect(owner_url()) as conn:
    text = (ROOT / "db/audit.sql").read_text()
    conn.execute(text[text.index("CREATE FUNCTION lock_audit_chain") :])
    conn.execute("GRANT EXECUTE ON FUNCTION lock_audit_chain(uuid) TO shiksham_runtime")
with (ROOT / "docs/overnight-log.md").open("a", encoding="utf-8") as f:
    f.write(
        "\n- Audit integration defect: SELECT FOR UPDATE requires UPDATE privileges, while runtime is forbidden UPDATE on audit_chains. Added a fixed-search-path SECURITY DEFINER lock helper, preserving the runtime privilege boundary. Applied helper locally; fresh migration includes it.\n"
    )
