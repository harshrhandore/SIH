"""Authentication policy and transaction boundaries."""

from app.core.clock import utc_now


import hmac
from app.core.errors import fail
from app.core.security import hash_token, issue, password_ok, public_user
from app.db.session import connect
from app.modules.auth import repository


def login(email, password):
    if len(password.encode("utf-8")) > 72:
        fail("PASSWORD_TOO_LONG", 422)
    with connect() as conn:
        user = repository.active_user_by_email(conn, email)
        if not user or not password_ok(password, user["password_hash"]):
            fail("INVALID_CREDENTIALS", 401, "Email or password is invalid.")
        return issue(conn, user)


def refresh(refresh_token, csrf_token):
    reused = False
    with connect() as conn:
        session = repository.locked_session(conn, hash_token(refresh_token))
        if not session or session["expires_at"] < utc_now():
            fail("REFRESH_EXPIRED", 401)
        if session["rotated_at"] or session["revoked_at"]:
            repository.revoke_family(conn, session["family_id"])
            reused = True
        elif not hmac.compare_digest(hash_token(csrf_token), session["csrf_hash"]):
            fail("CSRF_INVALID", 403)
        else:
            repository.rotate_session(conn, session["id"])
            user = repository.active_user(conn, session["user_id"])
            if not user:
                fail("REFRESH_EXPIRED", 401)
            result = issue(conn, user, session["family_id"])
    # Raise after commit so token reuse revokes the whole family durably.
    if reused:
        fail("REFRESH_REUSED", 401)
    return result


def logout(user, all_sessions):
    with connect() as conn:
        if all_sessions:
            repository.revoke_user(conn, user["id"])
        else:
            repository.revoke_family(conn, user["sid"])
    return dict(logged_out=True)


def current_user(user):
    with connect() as conn:
        return public_user(conn, user)
