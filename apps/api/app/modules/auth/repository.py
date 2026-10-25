"""Session persistence. Callers own the transaction and lock lifetime."""

from app.db.session import one


def active_user_by_email(conn, email):
    return one(conn, "SELECT * FROM users WHERE lower(email)=%s AND active", (email.strip().casefold(),))


def active_user(conn, user_id):
    return one(conn, "SELECT * FROM users WHERE id=%s AND active", (user_id,))


def locked_session(conn, token_hash):
    return one(conn, "SELECT * FROM refresh_sessions WHERE token_hash=%s FOR UPDATE", (token_hash,))


def revoke_family(conn, family_id):
    conn.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE family_id=%s", (family_id,))


def revoke_user(conn, user_id):
    conn.execute("UPDATE refresh_sessions SET revoked_at=now() WHERE user_id=%s", (user_id,))


def rotate_session(conn, session_id):
    conn.execute("UPDATE refresh_sessions SET rotated_at=now() WHERE id=%s", (session_id,))
