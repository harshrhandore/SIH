"""Run the fixed security-definer refresh in a background transaction."""

from app.db.session import connect
from app.modules.analytics import repository


def run():
    with connect() as conn:
        return repository.refresh_query(conn, ()).fetchone()
